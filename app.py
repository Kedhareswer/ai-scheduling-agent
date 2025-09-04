import streamlit as st
from datetime import datetime
import os

# Import utils
from utils.patient_lookup import PatientLookup
from utils.scheduler import Scheduler
from utils.reminder_system import ReminderSystem
from utils.email_sender import EmailSender
from utils.sms_sender import SMSSender
from utils.admin_exporter import AdminExporter
from utils.agents import SchedulingAgentOrchestrator

# ----------------------------
# Initialize Utilities
# ----------------------------
patient_lookup = PatientLookup("Data/patients.csv")
scheduler = Scheduler("Data/doctor_schedule.xlsx")
reminder = ReminderSystem()
emailer = EmailSender("Forms/New Patient Intake Form.pdf")
sms = SMSSender()
exporter = AdminExporter()

# Initialize LangGraph Multi-Agent Orchestrator (NEW - meets PDF requirements)
orchestrator = SchedulingAgentOrchestrator()

# ----------------------------
# Streamlit UI Setup
# ----------------------------
st.set_page_config(page_title="AI Scheduling Agent", layout="centered")
st.title("🏥 AI Scheduling Agent")

# Sidebar Health Check
with st.sidebar:
    st.header("System Health")

    def check_path(path: str, label: str):
        if os.path.exists(path):
            st.success(f"{label} ✓")
        else:
            st.error(f"{label} missing: {path}")

    check_path("Data/patients.csv", "Patients CSV")
    check_path("Data/doctor_schedule.xlsx", "Schedule Excel")
    check_path("Forms/New Patient Intake Form.pdf", "Intake Form PDF")

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        st.success("OPENAI_API_KEY detected ✓")
        st.info("🤖 LangGraph Multi-Agent System: ENABLED")
        st.info("🔧 LangChain Tools: ENABLED")
        st.info("🧠 LLM: GPT-4o-mini")
    else:
        st.warning("OPENAI_API_KEY not set. Using local CSV lookup (recommended for offline).")
        
    # Workflow mode selector
    st.subheader("Workflow Mode")
    use_langgraph = st.checkbox("Use LangGraph Multi-Agent Orchestration", value=bool(openai_key))
    if use_langgraph and not openai_key:
        st.error("LangGraph requires OPENAI_API_KEY")

# Chat state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "step" not in st.session_state:
    st.session_state.step = "greeting"
if "patient" not in st.session_state:
    st.session_state.patient = {}
if "use_langgraph" not in st.session_state:
    st.session_state.use_langgraph = bool(os.getenv("OPENAI_API_KEY"))

# On first load, show the greeting message without waiting for user input
if st.session_state.step == "greeting" and not any(m.get("role") == "assistant" for m in st.session_state.messages):
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": "Hello! Please provide your full name and Date of Birth (YYYY-MM-DD).",
        }
    )

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ----------------------------
# Chat Input Handling
# ----------------------------
if prompt := st.chat_input("Type your response..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Update LangGraph usage preference
    use_langgraph = st.session_state.get("use_langgraph", bool(os.getenv("OPENAI_API_KEY")))
    
    # NEW: LangGraph Multi-Agent Orchestration Path
    if use_langgraph and os.getenv("OPENAI_API_KEY"):
        try:
            # Use LangGraph multi-agent system for complete workflow
            result = orchestrator.process_patient_request(prompt)
            
            # Display agent messages
            for msg in result.get("messages", []):
                st.session_state.messages.append({"role": "assistant", "content": msg})
            
            # Handle any errors
            if result.get("errors"):
                error_msg = "🚨 Multi-Agent System Errors: " + "; ".join(result["errors"])
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            
            # Mark as complete
            st.session_state.step = "done"
            # Rerun to immediately display assistant messages
            st.experimental_rerun()
            
        except Exception as e:
            st.session_state.messages.append(
                {"role": "assistant", "content": f"❌ LangGraph Error: {str(e)}. Falling back to manual workflow."}
            )
            # Fall back to manual workflow
            use_langgraph = False
            # Rerun to show the error assistant message
            st.experimental_rerun()
    
    # EXISTING: Manual Step-by-Step Workflow (Fallback)
    if not use_langgraph:
        # Step 1: Greeting - process first input immediately
        if st.session_state.step == "greeting":
            st.session_state.step = "lookup"
            # Process the input as a lookup request immediately (fall through to next if)

        # Step 2: Patient Lookup
    if st.session_state.step == "lookup":
        try:
            # Split into 2 parts: Name, DOB
            parts = prompt.split(",")
            if len(parts) != 2:
                raise ValueError("Invalid format")

            name = parts[0].strip()
            dob_str = parts[1].strip()

            # Validate DOB format
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()

            # LangChain lookup
            response = patient_lookup.find_patient(name, str(dob))

            if response:  # Returning patient
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"✅ Found returning patient record:\n{response}"}
                )
                st.session_state.patient["Name"] = name
                st.session_state.patient["DOB"] = str(dob)
                st.session_state.patient["Status"] = "Returning"
            else:  # New patient
                st.session_state.messages.append(
                    {"role": "assistant", "content": f"Looks like you are a new patient, {name}. Let's continue with insurance details."}
                )
                st.session_state.patient["Name"] = name
                st.session_state.patient["DOB"] = str(dob)
                st.session_state.patient["Status"] = "New"

            # Ask for preferences before insurance, as per requirements
            st.session_state.messages.append(
                {"role": "assistant", "content": "Do you have a preferred Doctor and Location? If yes, enter: Doctor, Location. If no, type 'any'."}
            )
            st.session_state.step = "preferences"

        except Exception:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Please enter format: Name, YYYY-MM-DD (e.g., John Doe, 1985-02-14)."}
            )

    # Step 3a: Preferences (Doctor / Location)
    elif st.session_state.step == "preferences":
        try:
            if prompt.strip().lower() == "any":
                st.session_state.patient["PreferredDoctor"] = None
                st.session_state.patient["PreferredLocation"] = None
            else:
                parts = prompt.split(",")
                if len(parts) != 2:
                    raise ValueError("Invalid format")
                st.session_state.patient["PreferredDoctor"] = parts[0].strip()
                st.session_state.patient["PreferredLocation"] = parts[1].strip()

            # Move to insurance step
            st.session_state.messages.append(
                {"role": "assistant", "content": "Please provide your Insurance Carrier, Member ID, and Group Number (comma separated)."}
            )
            st.session_state.step = "insurance"

        except Exception:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Please enter 'any' or: Doctor, Location"}
            )

    # Step 3b: Insurance Capture
    elif st.session_state.step == "insurance":
        try:
            parts = prompt.split(",")
            if len(parts) != 3:
                raise ValueError("Invalid format")

            carrier = parts[0].strip()
            member_id = parts[1].strip()
            group_num = parts[2].strip()

            st.session_state.patient["InsuranceCarrier"] = carrier
            st.session_state.patient["MemberID"] = member_id
            st.session_state.patient["GroupNumber"] = group_num

            st.session_state.messages.append(
                {"role": "assistant", "content": f"✅ Insurance recorded: {carrier}, Member ID: {member_id}, Group: {group_num}"}
            )
            # Collect contact details next for email/SMS confirmations
            st.session_state.messages.append(
                {"role": "assistant", "content": "Please provide your Email and Phone (comma separated), e.g., name@example.com, +1-555-123-4567"}
            )
            st.session_state.step = "contact"

        except Exception:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Please enter format: Carrier, MemberID, GroupNumber"}
            )

    # Step 3c: Contact details
    elif st.session_state.step == "contact":
        try:
            parts = prompt.split(",")
            if len(parts) != 2:
                raise ValueError("Invalid format")
            email = parts[0].strip()
            phone = parts[1].strip()
            st.session_state.patient["Email"] = email
            st.session_state.patient["Phone"] = phone

            st.session_state.messages.append(
                {"role": "assistant", "content": f"✅ Contact saved: {email}, {phone}"}
            )
            st.session_state.step = "scheduling"

        except Exception:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Please enter format: email@example.com, +1-555-123-4567"}
            )

    # Step 4: Smart Scheduling
    elif st.session_state.step == "scheduling":
        duration = 60 if st.session_state.patient.get("Status") == "New" else 30
        slots = scheduler.get_available_slots(
            doctor=st.session_state.patient.get("PreferredDoctor"),
            location=st.session_state.patient.get("PreferredLocation"),
        )

        if slots.empty:
            st.session_state.messages.append(
                {"role": "assistant", "content": "🚫 No available slots at the moment. Please try again later or contact the office."}
            )
            st.session_state.step = "done"
        else:
            # Persist the current slots view so the chosen index maps correctly to the schedule row
            st.session_state["slots_view"] = slots
            slot_lines = []
            for i, row in slots.iterrows():
                doctor = row.get('DoctorName', row.get('Doctor', row.get('Provider', 'Doctor')))
                date = row.get('Date', row.get('Day', row.get('AppointmentDate', 'Date')))
                time_slot = row.get('TimeSlot', row.get('Time', row.get('Slot', 'Time')))
                slot_lines.append(f"{len(slot_lines)+1}. {doctor} - {date} {time_slot}")
            slot_text = "\n".join(slot_lines)

            st.session_state.messages.append(
                {"role": "assistant", "content": f"Here are available slots (Duration: {duration} mins):\n{slot_text}\n\nPlease pick a slot number."}
            )
            st.session_state.step = "confirmation"

    # Step 5: Appointment Confirmation + Form + Reminder
    elif st.session_state.step == "confirmation":
        try:
            choice = int(prompt) - 1
            slots_view = st.session_state.get("slots_view")
            if slots_view is None or choice < 0 or choice >= len(slots_view):
                raise ValueError("Invalid slot selection")
            selected_row = slots_view.iloc[choice]
            chosen = scheduler.book_slot_by_row_index(selected_row.name)

            doctor = chosen.get('DoctorName', chosen.get('Doctor', chosen.get('Provider', 'Doctor')))
            date = chosen.get('Date', chosen.get('Day', chosen.get('AppointmentDate', 'Date')))
            time_slot = chosen.get('TimeSlot', chosen.get('Time', chosen.get('Slot', 'Time')))

            st.session_state.messages.append(
                {"role": "assistant", "content": f"✅ Appointment confirmed with {doctor} on {date} at {time_slot}!"}
            )

            # Send intake form
            email_to = st.session_state.patient.get("Email", "test_patient@example.com")
            phone_to = st.session_state.patient.get("Phone", "+1-555-000-0000")
            email_msg = emailer.send_intake_form(email_to)
            st.session_state.messages.append(
                {"role": "assistant", "content": email_msg}
            )

            # Export appointment for admin review
            exporter.append_appointment({
                "Name": st.session_state.patient.get("Name"),
                "DOB": st.session_state.patient.get("DOB"),
                "Status": st.session_state.patient.get("Status"),
                "InsuranceCarrier": st.session_state.patient.get("InsuranceCarrier"),
                "MemberID": st.session_state.patient.get("MemberID"),
                "GroupNumber": st.session_state.patient.get("GroupNumber"),
                "Email": email_to,
                "Phone": phone_to,
                "Doctor": doctor,
                "Date": date,
                "Time": time_slot,
                "DurationMins": 60 if st.session_state.patient.get("Status") == "New" else 30,
            })

            # First reminder simulation (email + SMS + log)
            reminder_msg = reminder.send_reminder(st.session_state.patient["Name"], 1)
            st.session_state.messages.append(
                {"role": "assistant", "content": f"📅 Reminder scheduled: {reminder_msg}"}
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": emailer.send_email(email_to, reminder_msg)}
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": sms.send_sms(phone_to, reminder_msg)}
            )

            # Ask for actions for 2nd and 3rd reminders
            st.session_state.messages.append(
                {"role": "assistant", "content": "For the next reminders: 2) Have you filled the forms? 3) Is your visit confirmed? If not, provide reason.\nPlease reply in the format: forms=<yes/no>, confirm=<yes/no>, reason=<text or NA>"}
            )

            st.session_state.step = "reminders_action"

        except Exception:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Invalid choice. Please select a valid slot number."}
            )

    # Step 6: Handle reminder actions (2nd and 3rd reminders)
    elif st.session_state.step == "reminders_action":
        try:
            # Basic parser for key=value, key=value, key=value
            text = prompt.strip()
            parts = [p.strip() for p in text.split(",")]
            kv = {}
            for p in parts:
                if "=" in p:
                    k, v = p.split("=", 1)
                    kv[k.strip().lower()] = v.strip()

            filled = kv.get("forms", "").lower() in ("yes", "y", "true")
            confirmed = kv.get("confirm", "").lower() in ("yes", "y", "true")
            reason = kv.get("reason", "NA")

            patient_name = st.session_state.patient.get("Name", "Patient")
            email_to = st.session_state.patient.get("Email", "test_patient@example.com")
            phone_to = st.session_state.patient.get("Phone", "+1-555-000-0000")

            # Second reminder with action
            msg2 = f"Have you filled the forms? Our record: {'Yes' if filled else 'No'}"
            st.session_state.messages.append({"role": "assistant", "content": msg2})
            emailer.send_email(email_to, msg2)
            sms.send_sms(phone_to, msg2)
            reminder.send_reminder(patient_name, 2)

            # Third reminder with action
            if confirmed:
                msg3 = "Your visit is confirmed. See you soon!"
            else:
                msg3 = f"Your visit is not confirmed. Reason for cancellation: {reason}"
            st.session_state.messages.append({"role": "assistant", "content": msg3})
            emailer.send_email(email_to, msg3)
            sms.send_sms(phone_to, msg3)
            reminder.send_reminder(patient_name, 3)

            st.session_state.messages.append({"role": "assistant", "content": "✅ Workflow complete."})
            st.session_state.step = "done"

        except Exception:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Please reply like: forms=yes, confirm=no, reason=Not feeling well"}
            )
