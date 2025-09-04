import streamlit as st
from datetime import datetime

# Import utils
from utils.patient_lookup import PatientLookup
from utils.scheduler import Scheduler
from utils.reminder_system import ReminderSystem
from utils.email_sender import EmailSender

# ----------------------------
# Initialize Utilities
# ----------------------------
patient_lookup = PatientLookup("data/patients.csv")
scheduler = Scheduler("data/doctor_schedule.xlsx")
reminder = ReminderSystem()
emailer = EmailSender("forms/New_Patient_Intake_Form.pdf")

# ----------------------------
# Streamlit UI Setup
# ----------------------------
st.set_page_config(page_title="AI Scheduling Agent", layout="centered")
st.title("🏥 AI Scheduling Agent")

# Chat state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "step" not in st.session_state:
    st.session_state.step = "greeting"
if "patient" not in st.session_state:
    st.session_state.patient = {}

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ----------------------------
# Chat Input Handling
# ----------------------------
if prompt := st.chat_input("Type your response..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Step 1: Greeting
    if st.session_state.step == "greeting":
        st.session_state.messages.append(
            {"role": "assistant", "content": "Hello! Please provide your full name and Date of Birth (YYYY-MM-DD)."}
        )
        st.session_state.step = "lookup"

    # Step 2: Patient Lookup
    elif st.session_state.step == "lookup":
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

            # Move to insurance step
            st.session_state.messages.append(
                {"role": "assistant", "content": "Please provide your Insurance Carrier, Member ID, and Group Number (comma separated)."}
            )
            st.session_state.step = "insurance"

        except Exception:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Please enter format: Name, YYYY-MM-DD (e.g., John Doe, 1985-02-14)."}
            )

    # Step 3: Insurance Capture
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
            st.session_state.step = "scheduling"

        except Exception:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Please enter format: Carrier, MemberID, GroupNumber"}
            )

    # Step 4: Smart Scheduling
    elif st.session_state.step == "scheduling":
        duration = 60 if st.session_state.patient.get("Status") == "New" else 30
        slots = scheduler.get_available_slots()

        slot_text = "\n".join(
            [f"{i+1}. {row['DoctorName']} - {row['Date']} {row['TimeSlot']}" for i, row in slots.iterrows()]
        )

        st.session_state.messages.append(
            {"role": "assistant", "content": f"Here are available slots (Duration: {duration} mins):\n{slot_text}\n\nPlease pick a slot number."}
        )
        st.session_state.step = "confirmation"

    # Step 5: Appointment Confirmation + Form + Reminder
    elif st.session_state.step == "confirmation":
        try:
            choice = int(prompt) - 1
            chosen = scheduler.book_slot(choice)

            if not chosen:
                raise ValueError("Invalid slot selection")

            st.session_state.messages.append(
                {"role": "assistant", "content": f"✅ Appointment confirmed with {chosen['DoctorName']} on {chosen['Date']} at {chosen['TimeSlot']}!"}
            )

            # Send intake form
            email_msg = emailer.send_intake_form("test_patient@example.com")
            st.session_state.messages.append(
                {"role": "assistant", "content": email_msg}
            )

            # First reminder simulation
            reminder_msg = reminder.send_reminder(st.session_state.patient["Name"], 1)
            st.session_state.messages.append(
                {"role": "assistant", "content": f"📅 Reminder scheduled: {reminder_msg}"}
            )

            st.session_state.step = "done"

        except Exception:
            st.session_state.messages.append(
                {"role": "assistant", "content": "❌ Invalid choice. Please select a valid slot number."}
            )
