"""
Utility script for testing the vision model capabilities.
"""
import os
import sys
# Set up path to allow imports from app
sys.path.append(os.getcwd())

from groq import Groq

# Using environment variable for key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

def test_models():
    """
    Sends a sample 1x1 image to the vision model to verify API connectivity and response format.
    """
    print(f"Testing vision on {MODEL}...")
    
    # 1x1 pixel transparent gif base64
    base64_image = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/gif;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            temperature=0.1,
        )
        print(f"SUCCESS! Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_models()
