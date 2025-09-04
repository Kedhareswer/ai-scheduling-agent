import datetime

class ReminderSystem:
    def __init__(self, log_file="outputs/reminders_log.txt"):
        self.log_file = log_file

    def send_reminder(self, patient_name, step):
        """Simulate sending reminders"""
        messages = {
            1: f"Reminder: Hi {patient_name}, you have an upcoming appointment. Please confirm.",
            2: f"Reminder: Hi {patient_name}, have you filled out your intake form?",
            3: f"Reminder: Hi {patient_name}, is your visit confirmed? If not, please provide reason for cancellation."
        }
        msg = messages.get(step, "Unknown reminder step.")

        with open(self.log_file, "a") as f:
            f.write(f"{datetime.datetime.now()} - {msg}\n")

        return msg
