import pandas as pd
import os

class Scheduler:
    def __init__(self, schedule_file: str):
        self.schedule_file = schedule_file
        # Load schedule safely; if file missing or unreadable, fall back to an empty DataFrame
        try:
            if os.path.exists(schedule_file):
                self.df = pd.read_excel(schedule_file)
            else:
                self.df = pd.DataFrame(columns=["DoctorName", "Date", "TimeSlot", "Status", "Location"])
        except Exception:
            self.df = pd.DataFrame(columns=["DoctorName", "Date", "TimeSlot", "Status", "Location"])

    def get_available_slots(self, limit=5, doctor=None, location=None):
        """Return available slots, optionally filtered by doctor and location.

        Column name variations are handled for availability, doctor, and location.
        """
        df = self.df.copy()

        # Availability mask
        if "Status" in df.columns:
            mask = df["Status"].astype(str).str.strip().str.lower().eq("available")
        elif "Available" in df.columns:
            avail_col = df["Available"].astype(str).str.strip().str.lower()
            mask = avail_col.isin(["yes", "true", "1", "available"])
        else:
            mask = pd.Series([True] * len(df), index=df.index)

        filtered = df[mask]

        # Helper to find a column by synonyms
        def find_col(cols, candidates):
            for c in candidates:
                if c in cols:
                    return c
            return None

        # Doctor filter
        if doctor:
            doctor_col = find_col(
                filtered.columns,
                ["DoctorName", "Doctor", "Provider", "Physician", "Doctor Name"],
            )
            if doctor_col:
                filtered = filtered[filtered[doctor_col].astype(str).str.strip().str.lower() == str(doctor).strip().lower()]

        # Location filter
        if location:
            location_col = find_col(
                filtered.columns, ["Location", "Clinic", "Branch", "Site", "Office"]
            )
            if location_col:
                filtered = filtered[
                    filtered[location_col].astype(str).str.strip().str.lower()
                    == str(location).strip().lower()
                ]

        return filtered.head(limit)

    def book_slot_by_row_index(self, row_index: int):
        """Mark the given row index as booked and persist the schedule."""
        if row_index not in self.df.index:
            return None

        if "Status" in self.df.columns:
            self.df.loc[row_index, "Status"] = "Booked"
        elif "Available" in self.df.columns:
            if self.df["Available"].dtype == bool:
                self.df.loc[row_index, "Available"] = False
            else:
                self.df.loc[row_index, "Available"] = "No"

        # Persist back to the original schedule file
        self.save()
        return self.df.loc[row_index].to_dict()

    # Backwards-compat shim (kept for compatibility if used elsewhere)
    def book_slot(self, slot_index: int):
        available = self.get_available_slots(limit=5)
        if slot_index >= len(available):
            return None
        chosen = available.iloc[slot_index]
        return self.book_slot_by_row_index(chosen.name)

    def save(self):
        """Persist the in-memory schedule to its original file."""
        # Ensure directory exists for safety (usually Data/)
        out_dir = os.path.dirname(self.schedule_file)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        self.df.to_excel(self.schedule_file, index=False)
