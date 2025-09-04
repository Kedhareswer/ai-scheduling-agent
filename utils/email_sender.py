import os

class EmailSender:
    def __init__(self, form_path="forms/New_Patient_Intake_Form.pdf"):
        self.form_path = form_path

    def send_intake_form(self, patient_email):
        """Simulate sending intake form (replace with real email API if needed)"""
        if os.path.exists(self.form_path):
            return f"📧 Sent intake form to {patient_email} ({self.form_path})"
        return "⚠️ Intake form not found!"
