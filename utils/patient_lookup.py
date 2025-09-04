from langchain_experimental.agents.agent_toolkits import create_csv_agent
from langchain_openai import ChatOpenAI
import os
import pandas as pd
from dotenv import load_dotenv

class PatientLookup:
    def __init__(self, patients_csv):
        load_dotenv()
        self.patients_csv = patients_csv
        self.agent = None
        openai_api_key = os.getenv("OPENAI_API_KEY")
        # Initialize the agent only if an API key is available; otherwise, fallback to local CSV lookup
        if openai_api_key:
            try:
                self.agent = create_csv_agent(
                    ChatOpenAI(
                        model="gpt-4o-mini",
                        temperature=0,
                        openai_api_key=openai_api_key
                    ),
                    patients_csv,
                    verbose=False,
                    allow_dangerous_code=True
                )
            except Exception:
                # If agent creation fails for any reason, continue with local lookup only
                self.agent = None

    def find_patient(self, name: str, dob: str):
        """
        Find a patient by exact Name and DOB in the CSV.
        Returns a string summary if found, otherwise None.
        """
        try:
            df = pd.read_csv(self.patients_csv, dtype=str).fillna("")
            if "Name" not in df.columns or "DOB" not in df.columns:
                return None

            target_name = name.strip().lower()
            target_dob = dob.strip()

            mask = (
                df["Name"].str.strip().str.lower() == target_name
            ) & (
                df["DOB"].astype(str).str.strip() == target_dob
            )

            if not mask.any():
                return None

            row = df[mask].iloc[0]

            parts = []

            def add_if_present(col, label=None):
                if col in df.columns:
                    val = str(row[col]).strip()
                    if val:
                        parts.append(f"{label or col}: {val}")

            add_if_present("Name")
            add_if_present("DOB")
            add_if_present("InsuranceCarrier", "Insurance")
            add_if_present("MemberID", "Member ID")
            add_if_present("GroupNumber", "Group")
            add_if_present("Status")

            return ", ".join(parts)
        except Exception:
            return None
