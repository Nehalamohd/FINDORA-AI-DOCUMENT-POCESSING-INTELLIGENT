"""
Evaluation module for generating golden Q&A pairs and scoring RAG answers using LLM-as-a-judge.
"""
import json
import random
from app.database import SessionLocal
from app.models import Chunk, Document, GoldenQA
from app.llm import client
from app.logger import logger


def generate_golden_questions(flow_id: str, num_questions: int = 5):
    """
    Generates ground-truth Q&A pairs from documents in a specific flow.
    
    Args:
        flow_id (str): UUID of the flow.
        num_questions (int): Number of pairs to generate.
        
    Returns:
        dict: Success message and count or error details.
    """
    
    #Generates golden Q&A pairs from the documents in the specified flow.
    
    db = SessionLocal()
    try:
        # 1. Fetch chunk content belongs to document  filtered by flow_id
        # match each chunk to its document to filter under a specifice flow_id
        rows = db.query(Chunk.content).join(Document, Chunk.document_id == Document.id).filter(Document.flow_id == flow_id).all()
    except Exception as e:
        logger.error(f"Error fetching chunks for golden question generation: {str(e)}")
        return {"error": f"Database error: {str(e)}"}
    finally:
        db.close()
     # if rows is empty       
    if not rows:
        logger.warning(f"No documents found in flow {flow_id} to generate questions from.")
        return {"error": "No documents found in this flow to generate questions from."}
    
    # 2. Select random chunks to generate questions 
    #to convert list of dict to list of string
    chunks = [r[0] for r in rows]
    # Simple strategy: take random sample or 
    # combine a few into one single string

    selected_context = "\n\n".join(random.sample(chunks, min(len(chunks), 3)))
    #Instruction or prompt for the LLM
    prompt = f"""
    You are an expert evaluator. Given the following text, generate {num_questions} diverse question and answer pairs.
    The questions should be specific and the answers should be accurate based ONLY on the text.
    
    Output the result as a raw VALID JSON list of objects, like this:
    [
        {{"question": "What is...", "answer": "It is..."}},
        {{"question": "How does...", "answer": "By..."}}
    ]
    
    Text:
    {selected_context}
    """
    #model reads the text and 
    # invents questions and answers based on it
    
    #send prompt to ai model
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content
        #  Parse JSON from response may be llm add extra text
        start = content.find('[')
        end = content.rfind(']') + 1
        if start == -1 or end == 0:
            return {"error": "Failed to parse JSON from LLM response"}
            
        qa_pairs = json.loads(content[start:end])
        
        #  Save to database
        saved_count = 0
        db = SessionLocal()
        try:
            for qa in qa_pairs:
                #new row in GoldenQA table
                golden = GoldenQA(flow_id=flow_id, question=qa['question'], expected_answer=qa['answer'])
                db.add(golden)
                saved_count += 1
            db.commit()
            logger.info(f"Generated and saved {saved_count} golden Q&A pairs for flow {flow_id}")
        except Exception as save_e:
            logger.error(f"Error saving golden Q&A pairs: {str(save_e)}")
            db.rollback()
        finally:
            db.close()
                
        return {"message": f"Successfully generated and saved {saved_count} golden Q&A pairs."}
        
    except Exception as e:
        logger.error(f"Error generating golden questions: {str(e)}", exc_info=True)
        return {"error": str(e)}

#for evaluating answers provided by the LLM
#pass question, expected answer, generated answer
def evaluate_answer(question: str, expected_answer: str, generated_answer: str):
    """
    Uses LLM-as-a-judge to score the generated answer against the expected answer.
    """
    prompt = f"""
    Compare the Generated Answer with the Expected Answer for the given Question.
    
    # we give

    Question: {question}
    Expected Answer: {expected_answer}
    Generated Answer: {generated_answer}
    
    Rate the Generated Answer on a scale of 0.0 to 1.0 based on accuracy and completeness.
    Provide a brief explanation for your score.
    
    Output JSON format:
    {{
        "score": 0.8,
        "feedback": "The answer covers the main points but misses..."
    }}
    """
    
    try:
        #send prompt to llm 
        #llm compr exp vs generated answer

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        # only need text part
        content = response.choices[0].message.content
        
        start = content.find('{')
        end = content.rfind('}') + 1
        result = json.loads(content[start:end])
        
        return result
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}", exc_info=True)
        return {"score": 0.0, "feedback": "Error during evaluation"}
