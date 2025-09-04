from typing import Dict, Any, List, TypedDict, Annotated
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
import pandas as pd
import os
from datetime import datetime

# Import our existing utilities
from .patient_lookup import PatientLookup
from .scheduler import Scheduler
from .email_sender import EmailSender
from .sms_sender import SMSSender
from .admin_exporter import AdminExporter
from .reminder_system import ReminderSystem
from .llm_provider import get_llm_provider

class AgentState(TypedDict):
    """State shared across all agents in the LangGraph workflow"""
    patient_input: str
    patient_data: Dict[str, Any]
    available_slots: List[Dict[str, Any]]
    selected_slot: Dict[str, Any]
    messages: List[str]
    current_step: str
    errors: List[str]

class SchedulingAgentOrchestrator:
    """Multi-agent orchestration using LangGraph for medical appointment scheduling"""
    
    def __init__(self):
        # Initialize flexible LLM provider
        self.llm_provider = get_llm_provider()
        self.llm = self.llm_provider.llm
        
        # Initialize utilities
        self.patient_lookup = PatientLookup("Data/patients.csv")
        self.scheduler = Scheduler("Data/doctor_schedule.xlsx")
        self.emailer = EmailSender("Forms/New Patient Intake Form.pdf")
        self.sms = SMSSender()
        self.exporter = AdminExporter()
        self.reminder = ReminderSystem()
        
        # Build the multi-agent graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with multiple specialized agents"""
        workflow = StateGraph(AgentState)
        
        # Add agent nodes
        workflow.add_node("patient_agent", self.patient_agent)
        workflow.add_node("scheduler_agent", self.scheduler_agent)
        workflow.add_node("confirmation_agent", self.confirmation_agent)
        workflow.add_node("communication_agent", self.communication_agent)
        workflow.add_node("error_handler", self.error_handler)
        
        # Define the workflow edges
        workflow.add_edge(START, "patient_agent")
        workflow.add_conditional_edges(
            "patient_agent",
            self._route_after_patient,
            {
                "schedule": "scheduler_agent",
                "error": "error_handler"
            }
        )
        workflow.add_conditional_edges(
            "scheduler_agent", 
            self._route_after_scheduler,
            {
                "confirm": "confirmation_agent",
                "error": "error_handler"
            }
        )
        workflow.add_conditional_edges(
            "confirmation_agent",
            self._route_after_confirmation,
            {
                "communicate": "communication_agent",
                "error": "error_handler"
            }
        )
        workflow.add_edge("communication_agent", END)
        workflow.add_edge("error_handler", END)
        
        return workflow.compile()
    
    def patient_agent(self, state: AgentState) -> AgentState:
        """Agent specialized in patient data processing and validation"""
        try:
            # Parse patient input (name, DOB, preferences, insurance, contact)
            input_text = state["patient_input"]
            
            # Use LLM to structure patient data if available
            if self.llm and input_text:
                system_msg = SystemMessage(content="""
                You are a patient data extraction agent. Parse the input and extract:
                - Name
                - Date of Birth (YYYY-MM-DD format)
                - Preferred Doctor (if mentioned)
                - Preferred Location (if mentioned) 
                - Insurance Carrier, Member ID, Group Number (if mentioned)
                - Email and Phone (if mentioned)
                
                Return structured data as key-value pairs.
                """)
                
                human_msg = HumanMessage(content=input_text)
                response = self.llm.invoke([system_msg, human_msg])
                
                # Simple parsing - in production would use structured output
                patient_data = self._parse_llm_response(response.content)
            else:
                # Fallback to basic parsing
                patient_data = self._basic_parse_patient_input(input_text)
            
            # Lookup existing patient
            if patient_data.get("Name") and patient_data.get("DOB"):
                existing = self.patient_lookup.find_patient(
                    patient_data["Name"], 
                    patient_data["DOB"]
                )
                if existing:
                    patient_data["Status"] = "Returning"
                    patient_data["ExistingRecord"] = existing
                else:
                    patient_data["Status"] = "New"
            
            state["patient_data"] = patient_data
            state["current_step"] = "patient_processed"
            state["messages"].append(f"✅ Patient processed: {patient_data.get('Name', 'Unknown')}")
            
        except Exception as e:
            state["errors"].append(f"Patient Agent Error: {str(e)}")
            state["current_step"] = "error"
            
        return state
    
    def scheduler_agent(self, state: AgentState) -> AgentState:
        """Agent specialized in appointment scheduling logic"""
        try:
            patient_data = state["patient_data"]
            
            # Determine appointment duration based on patient type
            duration = 60 if patient_data.get("Status") == "New" else 30
            
            # Get available slots with preferences
            slots = self.scheduler.get_available_slots(
                limit=5,
                doctor=patient_data.get("PreferredDoctor"),
                location=patient_data.get("PreferredLocation")
            )
            
            if slots.empty:
                state["errors"].append("No available slots found")
                state["current_step"] = "error"
                return state
            
            # Convert to list for state serialization
            available_slots = []
            for idx, row in slots.iterrows():
                slot_data = row.to_dict()
                slot_data["row_index"] = idx
                available_slots.append(slot_data)
            
            state["available_slots"] = available_slots
            state["current_step"] = "slots_available"
            state["messages"].append(f"📅 Found {len(available_slots)} available slots (Duration: {duration}min)")
            
        except Exception as e:
            state["errors"].append(f"Scheduler Agent Error: {str(e)}")
            state["current_step"] = "error"
            
        return state
    
    def confirmation_agent(self, state: AgentState) -> AgentState:
        """Agent specialized in appointment confirmation and booking"""
        try:
            # For demo purposes, auto-select first available slot
            # In production, this would wait for user selection
            available_slots = state["available_slots"]
            if not available_slots:
                state["errors"].append("No slots to confirm")
                state["current_step"] = "error"
                return state
                
            selected_slot = available_slots[0]  # Auto-select first slot
            
            # Book the appointment
            booked_slot = self.scheduler.book_slot_by_row_index(selected_slot["row_index"])
            
            if not booked_slot:
                state["errors"].append("Failed to book selected slot")
                state["current_step"] = "error"
                return state
            
            state["selected_slot"] = booked_slot
            state["current_step"] = "appointment_booked"
            
            doctor = booked_slot.get('DoctorName', booked_slot.get('Doctor', 'Doctor'))
            date = booked_slot.get('Date', booked_slot.get('Day', 'Date'))
            time_slot = booked_slot.get('TimeSlot', booked_slot.get('Time', 'Time'))
            
            state["messages"].append(f"✅ Appointment confirmed with {doctor} on {date} at {time_slot}")
            
        except Exception as e:
            state["errors"].append(f"Confirmation Agent Error: {str(e)}")
            state["current_step"] = "error"
            
        return state
    
    def communication_agent(self, state: AgentState) -> AgentState:
        """Agent specialized in patient communications and admin tasks"""
        try:
            patient_data = state["patient_data"]
            selected_slot = state["selected_slot"]
            
            # Send intake form
            email = patient_data.get("Email", "test@example.com")
            phone = patient_data.get("Phone", "+1-555-000-0000")
            
            intake_msg = self.emailer.send_intake_form(email)
            state["messages"].append(intake_msg)
            
            # Export for admin review
            self.exporter.append_appointment({
                "Name": patient_data.get("Name"),
                "DOB": patient_data.get("DOB"),
                "Status": patient_data.get("Status"),
                "InsuranceCarrier": patient_data.get("InsuranceCarrier"),
                "MemberID": patient_data.get("MemberID"),
                "GroupNumber": patient_data.get("GroupNumber"),
                "Email": email,
                "Phone": phone,
                "Doctor": selected_slot.get('DoctorName', 'Doctor'),
                "Date": selected_slot.get('Date', 'Date'),
                "Time": selected_slot.get('TimeSlot', 'Time'),
                "DurationMins": 60 if patient_data.get("Status") == "New" else 30,
            })
            
            # Send reminders
            patient_name = patient_data.get("Name", "Patient")
            reminder_msg = self.reminder.send_reminder(patient_name, 1)
            
            self.emailer.send_email(email, reminder_msg)
            self.sms.send_sms(phone, reminder_msg)
            
            state["messages"].append("📧 Communications sent: intake form, admin export, reminders")
            state["current_step"] = "workflow_complete"
            
        except Exception as e:
            state["errors"].append(f"Communication Agent Error: {str(e)}")
            state["current_step"] = "error"
            
        return state
    
    def error_handler(self, state: AgentState) -> AgentState:
        """Agent specialized in error handling and recovery"""
        errors = state.get("errors", [])
        state["messages"].append(f"❌ Errors encountered: {'; '.join(errors)}")
        state["current_step"] = "error_handled"
        return state
    
    def _route_after_patient(self, state: AgentState) -> str:
        """Route decision after patient agent"""
        return "error" if state.get("errors") else "schedule"
    
    def _route_after_scheduler(self, state: AgentState) -> str:
        """Route decision after scheduler agent"""
        return "error" if state.get("errors") else "confirm"
    
    def _route_after_confirmation(self, state: AgentState) -> str:
        """Route decision after confirmation agent"""
        return "error" if state.get("errors") else "communicate"
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured patient data"""
        # Simple parsing - in production would use structured output
        data = {}
        lines = response.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().replace(' ', '')
                value = value.strip()
                if value and value != 'None':
                    data[key] = value
        return data
    
    def _basic_parse_patient_input(self, input_text: str) -> Dict[str, Any]:
        """Basic fallback parsing when LLM is not available"""
        # Simple comma-separated parsing
        parts = [p.strip() for p in input_text.split(',')]
        data = {}
        
        if len(parts) >= 2:
            data["Name"] = parts[0]
            data["DOB"] = parts[1]
        if len(parts) >= 4:
            data["InsuranceCarrier"] = parts[2]
            data["MemberID"] = parts[3]
        if len(parts) >= 5:
            data["GroupNumber"] = parts[4]
            
        return data
    
    def process_patient_request(self, patient_input: str) -> Dict[str, Any]:
        """Main entry point for processing patient requests through the multi-agent system"""
        initial_state = AgentState(
            patient_input=patient_input,
            patient_data={},
            available_slots=[],
            selected_slot={},
            messages=[],
            current_step="start",
            errors=[]
        )
        
        # Execute the multi-agent workflow
        result = self.workflow.invoke(initial_state)
        
        return result
