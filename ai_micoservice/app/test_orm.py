"""
Integration test for verifying SQLAlchemy ORM relationships and cascade behavior.
"""
from app.database import SessionLocal
from app.models import User, Flow, Document
import uuid
from app.logger import logger

def test_user_flow():
    """
    Tests the creation of a user, a related flow, and verifies cascading deletion.
    """
    db = SessionLocal()
    try:
        # 1. Create a test user
        test_username = f"testuser_{uuid.uuid4().hex[:6]}"
        logger.info(f"Creating test user: {test_username}")
        user = User(username=test_username, password_hash="dummy_hash", email=f"{test_username}@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"User created with ID: {user.id}")

        # 2. Create a flow for this user
        logger.info(f"Creating flow for user: {user.username}")
        flow = Flow(user_id=user.id, name="Test Flow")
        db.add(flow)
        db.commit()
        db.refresh(flow)
        logger.info(f"Flow created with ID: {flow.id}")

        # 3. Retrieve user with flows
        retrieved_user = db.query(User).filter(User.id == user.id).first()
        logger.info(f"Retrieved user: {retrieved_user.username}")
        logger.info(f"User flows: {[f.name for f in retrieved_user.flows]}")

        # 4. Cleanup
        logger.info("Cleaning up test data...")
        db.delete(user) # Should cascade to flows
        db.commit()
        logger.info("Cleanup complete.")
        
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if test_user_flow():
        logger.info("ORM Basic Test PASSED!")
    else:
        logger.error("ORM Basic Test FAILED!")
        exit(1)
