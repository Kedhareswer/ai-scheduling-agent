import os

class EmailSender:
    def __init__(self, form_path="Forms/New Patient Intake Form.pdf"):
        self.form_path = form_path

    def send_intake_form(self, patient_email):
        """Simulate sending intake form (replace with real email API if needed)"""
        if os.path.exists(self.form_path):
            return f"📧 Sent intake form to {patient_email} ({self.form_path})"
        return "⚠️ Intake form not found!"

    def send_email(self, patient_email: str, message: str, log_file: str = "Output/email_log.txt") -> str:
        """Simulate sending a generic email by logging to a file and returning a status string."""
        out_dir = os.path.dirname(log_file)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{patient_email}: {message}\n")
        return f"📧 Email sent to {patient_email}: {message}"
