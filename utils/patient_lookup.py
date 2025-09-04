from langchain_experimental.agents.agent_toolkits import create_csv_agent
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

class PatientLookup:
    def __init__(self, patients_csv):
        load_dotenv()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it to your OpenAI API key.")
        self.agent = create_csv_agent(
            ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0,
                openai_api_key=openai_api_key
            ),
            patients_csv,
            verbose=True,
            allow_dangerous_code=True
        )
