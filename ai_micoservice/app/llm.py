from groq import Groq
from app.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)  

# for generating answers
#prompt is the question with context
# low temp for more precise answers
def generate_answer(prompt: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "helpful AI assistant for document-based question answering."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content

# for analyzing images
def analyze_image(base64_image: str, prompt: str = "Extract all text and structural data from this image in markdown format.") -> str:
    response = client.chat.completions.create(
        model="llama-3.2-11b-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content
