"""
Utility to list available Groq models for the service.
"""
import os
import sys
# Set up path to allow imports from app
sys.path.append(os.getcwd())

from groq import Groq
from app.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

def list_models():
    """
    Queries the Groq API for available models and prints their IDs.
    """
    try:
        models = client.models.list()
        print("Available Models:")
        for m in models.data:
            print(f"- {m.id}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
