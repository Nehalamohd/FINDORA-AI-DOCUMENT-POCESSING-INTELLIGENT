"""
Document Reviewer module for analyzing flow content and providing suggestions.
"""
from app.database import SessionLocal
from app.models import Page, Document
from app.llm import generate_answer
from app.logger import logger

#to interact with documents for review purposes
class DocumentReviewer:
    """
    Handles automated AI-based review of all documents within a flow.
    """
    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()

    def get_document_content(self, flow_id: str):
        """Aggregates all content from documents in a flow."""
        try:
            # Join Document and Page to get all text in the flow
            pages = (
                self.db.query(Page)
                .join(Document, Page.document_id == Document.id)
                .filter(Document.flow_id == flow_id)
                .order_by(Document.id, Page.page_number)
                .all()
            )
            return "\n".join([p.content for p in pages])
        except Exception as e:
            logger.error(f"Error retrieving flow content for review: {str(e)}")
            return ""
        finally:
            if not self.db:
                self.db.close()
    def review_document(self, flow_id: str):
        """
        Generates a comprehensive AI-based review report for all documents in a flow.
        
        This method aggregates specific document content, sends it to the LLM, 
        and returns a structured critique covering improvements, gaps, and an innovation score.

        Args:
            flow_id (str): The unique identifier of the document flow to review.

        Returns:
            dict: A dictionary containing either the 'review' text or an 'error' message.
        """
        logger.info(f"Starting document review for flow: {flow_id}")
        content = self.get_document_content(flow_id)
        if not content:
            logger.warning(f"No content found for review in flow: {flow_id}")
            return {"error": "No content found in this flow to review."}

        # Limiting to avoid context window issues for very large flows
        review_content = content[:10000]
        
        prompt = f"""
        You are an expert AI Document Reviewer. 
        Analyze the following document content and provide a detailed review report.
        
        Document Content:
        {review_content}
        
        Please provide your review in the following format:
        
        ### 1. Predicted Improvements
        - Suggestions for clarity, tone, and professional impact.
        - Specific sections that could be reworded.
        
        ### 2. Missing Sections & Gaps
        - Identify what is missing or what a reader might still be looking for.
        - Point out any logical gaps or missing proof points.
        
        ### 3. New Ideas & Innovations
        - Suggest creative follow-ups or ways to extend this document.
        - Propose new features or research directions related to the content.
        
        ### 4. Overall Quality Score (1-10): [Score]
        [Brief justification for the score]
        """
        
        try:
            review_text = generate_answer(prompt)
            logger.info(f"Document review completed for flow: {flow_id}")
            return {"review": review_text}
        except Exception as e:
            logger.error(f"Failed to generate review for flow {flow_id}: {str(e)}")
            return {"error": f"Review generation failed: {str(e)}"}
