import json
import random
from app.database import get_conn
from app.llm import client

def generate_golden_questions(flow_id: str, num_questions: int = 5):
    """
    Generates golden Q&A pairs from the documents in the specified flow.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. Fetch chunks from the flow
            cur.execute("""
                SELECT c.content 
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.flow_id = %s
            """, (flow_id,))
            rows = cur.fetchall()
            
    if not rows:
        return {"error": "No documents found in this flow to generate questions from."}
    
    # 2. Select random chunks to generate questions from
    chunks = [r["content"] for r in rows]
    # Simple strategy: take random sample or combine a few
    selected_context = "\n\n".join(random.sample(chunks, min(len(chunks), 3)))
    
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
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = response.choices[0].message.content
        # robust json parsing
        start = content.find('[')
        end = content.rfind(']') + 1
        if start == -1 or end == 0:
            return {"error": "Failed to parse JSON from LLM response"}
            
        qa_pairs = json.loads(content[start:end])
        
        # 3. Save to database
        saved_count = 0
        with get_conn() as conn:
            with conn.cursor() as cur:
                for qa in qa_pairs:
                    cur.execute(
                        "INSERT INTO golden_qa (flow_id, question, expected_answer) VALUES (%s, %s, %s)",
                        (flow_id, qa['question'], qa['answer'])
                    )
                    saved_count += 1
                conn.commit()
                
        return {"message": f"Successfully generated and saved {saved_count} golden Q&A pairs."}
        
    except Exception as e:
        print(f"Error generating golden questions: {e}")
        return {"error": str(e)}

def evaluate_answer(question: str, expected_answer: str, generated_answer: str):
    """
    Uses LLM-as-a-judge to score the generated answer against the expected answer.
    """
    prompt = f"""
    Compare the Generated Answer with the Expected Answer for the given Question.
    
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
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content
        
        start = content.find('{')
        end = content.rfind('}') + 1
        result = json.loads(content[start:end])
        
        return result
    except Exception as e:
        print(f"Evaluation error: {e}")
        return {"score": 0.0, "feedback": "Error during evaluation"}
