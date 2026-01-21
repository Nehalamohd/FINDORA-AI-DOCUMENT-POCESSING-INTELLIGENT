import os
import sys
# Set up path to allow imports from app
sys.path.append(os.getcwd())

from groq import Groq

# Using environment variable for key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

def list_models():
    try:
        models = client.models.list()
        print("Available Models:")
        for m in models.data:
            print(f"- {m.id}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
