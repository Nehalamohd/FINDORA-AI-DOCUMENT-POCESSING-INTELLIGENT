from app.database import SessionLocal
from app.models import Page, Document
from app.llm import generate_answer
from app.logger import logger

#to interact with documents for review purposes
class DocumentReviewer:
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
        finally:
            if not self.db:
                self.db.close()
#returns review of document in flow, with suggestions
#sends content to llm for review
#returns structured review
    def review_document(self, flow_id: str):
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
        
        review_text = generate_answer(prompt)
        logger.info(f"Document review completed for flow: {flow_id}")
        return {"review": review_text}
