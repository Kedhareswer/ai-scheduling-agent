import os
import pandas as pd
from datetime import datetime

class AdminExporter:
    def __init__(self, output_path: str = "Output/confirmed_appointments.xlsx"):
        self.output_path = output_path

    def append_appointment(self, record: dict):
        """Append a confirmed appointment to the Excel report for admin review."""
        out_dir = os.path.dirname(self.output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        # Ensure timestamp in record
        rec = {**record}
        rec.setdefault("ExportedAt", datetime.now().isoformat(timespec='seconds'))

        if os.path.exists(self.output_path):
            df = pd.read_excel(self.output_path)
            df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
        else:
            df = pd.DataFrame([rec])

        df.to_excel(self.output_path, index=False)
        return self.output_path
