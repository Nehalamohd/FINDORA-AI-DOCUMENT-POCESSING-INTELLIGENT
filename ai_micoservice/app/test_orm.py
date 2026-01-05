from app.database import SessionLocal
from app.models import User, Flow, Document
import uuid

def test_user_flow():
    db = SessionLocal()
    try:
        # 1. Create a test user
        test_username = f"testuser_{uuid.uuid4().hex[:6]}"
        print(f"Creating test user: {test_username}")
        user = User(username=test_username, password_hash="dummy_hash", email=f"{test_username}@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"User created with ID: {user.id}")

        # 2. Create a flow for this user
        print(f"Creating flow for user: {user.username}")
        flow = Flow(user_id=user.id, name="Test Flow")
        db.add(flow)
        db.commit()
        db.refresh(flow)
        print(f"Flow created with ID: {flow.id}")

        # 3. Retrieve user with flows
        retrieved_user = db.query(User).filter(User.id == user.id).first()
        print(f"Retrieved user: {retrieved_user.username}")
        print(f"User flows: {[f.name for f in retrieved_user.flows]}")

        # 4. Cleanup
        print("Cleaning up test data...")
        db.delete(user) # Should cascade to flows
        db.commit()
        print("Cleanup complete.")
        
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if test_user_flow():
        print("ORM Basic Test PASSED!")
    else:
        print("ORM Basic Test FAILED!")
        exit(1)
