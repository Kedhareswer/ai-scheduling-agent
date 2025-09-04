import os
from datetime import datetime

class SMSSender:
    def __init__(self, log_file: str = "Output/sms_log.txt"):
        self.log_file = log_file

    def send_sms(self, phone_number: str, message: str) -> str:
        """Simulate sending an SMS by logging to a file and returning a status string."""
        out_dir = os.path.dirname(self.log_file)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        entry = f"{datetime.now().isoformat(timespec='seconds')} -> {phone_number}: {message}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(entry)
        return f"📱 SMS sent to {phone_number}: {message}"
