from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db
from app.models import User
from sqlalchemy.orm import Session
from app.logger import logger

# Password hashing
#use pbkdf2_sha256 for password hashing
#convert password to garbled text before hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# for saying where to get the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
#for registering new users
def get_password_hash(password):
    return pwd_context.hash(password)
# for creating access tokens 
#expiry time
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
# to get current user or to set up protected routes
#FastAPI automatically reads the Authorization
#unauthorized access handling when authentication fails
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    #use alg or scrt key to decode token
    #jwt store username in sub field
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("JWT payload missing 'sub' field")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT validation failed: {str(e)}")
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    
    if user is None:
        logger.warning(f"Authenticated user '{username}' not found in database")
        raise credentials_exception
    
    return user
# to ensure user is active and authenticated
async def get_current_active_user(current_user: dict = Depends(get_current_user)):

    return current_user
