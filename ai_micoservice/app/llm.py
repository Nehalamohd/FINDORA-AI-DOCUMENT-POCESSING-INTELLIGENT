"""
LLM interface for generating answers and analyzing images using Groq.
"""
import time
from groq import Groq
from app.config import GROQ_API_KEY
from app.logger import logger

client = Groq(api_key=GROQ_API_KEY)  

#for backend , generating full answers from LLM
def generate_answer(prompt: str, model: str = "llama-3.1-8b-instant") -> str:
    """
    Generates a full answer from the LLM based on a prompt.
    """
    #used for which model to call
    logger.debug(f"Calling LLM ({model}) for generation")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are Findora AI, an expert assistant for document-based and general knowledge questions. Use the provided context (Documents and/or Web) to answer accurately."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        logger.info(f"LLM generation successful ({model})")
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM generation failed ({model}): {str(e)}")
        return f"Error: {str(e)}"

#for streaming partial answers from LLM
def generate_answer_stream(prompt: str, model: str = "llama-3.1-8b-instant"):
    """
    Generates a streaming answer from the LLM.
    """
    logger.info(f"Starting LLM stream ({model})")
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are Findora AI, an expert assistant for document-based and general knowledge questions. Use the provided context (Documents and/or Web) to answer accurately."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
        logger.info(f"LLM stream completed successfully ({model})")
    except Exception as e:
        logger.error(f"LLM stream failed ({model}): {str(e)}")
        yield f"__ERROR__:{str(e)}"

# for analyzing images with retry logic
def analyze_image(base64_image: str, prompt: str = "Extract all text and structural data from this image in markdown format.") -> str:
    """
    Analyzes an image using a vision model with retry logic.
    """
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
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
        except Exception as e:
            if "rate_limit_exceeded" in str(e).lower() and attempt < max_retries - 1:
                logger.warning(f"Rate limit hit, retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Vision model call failed: {str(e)}")
                raise e
