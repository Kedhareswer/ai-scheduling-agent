import pandas as pd

class Scheduler:
    def __init__(self, schedule_file: str):
        self.schedule_file = schedule_file
        self.df = pd.read_excel(schedule_file)

    def get_available_slots(self, limit=5):
        available = self.df[self.df["Status"] == "Available"].head(limit)
        return available

    def book_slot(self, slot_index: int, output_file="outputs/confirmed_appointments.xlsx"):
        available = self.df[self.df["Status"] == "Available"].head(5)
        if slot_index >= len(available):
            return None

        chosen = available.iloc[slot_index]
        self.df.loc[chosen.name, "Status"] = "Booked"
        self.df.to_excel(output_file, index=False)
        return chosen
