import datetime
import os

class ReminderSystem:
    def __init__(self, log_file="Output/reminders_log.txt"):
        self.log_file = log_file

    def send_reminder(self, patient_name, step):
        """Simulate sending reminders"""
        messages = {
            1: f"Reminder: Hi {patient_name}, you have an upcoming appointment. Please confirm.",
            2: f"Reminder: Hi {patient_name}, have you filled out your intake form?",
            3: f"Reminder: Hi {patient_name}, is your visit confirmed? If not, please provide reason for cancellation."
        }
        msg = messages.get(step, "Unknown reminder step.")

        # Ensure output directory exists before writing
        out_dir = os.path.dirname(self.log_file)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        with open(self.log_file, "a") as f:
            f.write(f"{datetime.datetime.now()} - {msg}\n")

        return msg
