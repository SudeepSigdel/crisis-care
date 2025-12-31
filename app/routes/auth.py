from fastapi import HTTPException, status, APIRouter, Depends
from sqlmodel import select
from .. import models, schemas, utils, database
from ..oauth2 import create_token
from fastapi.security.oauth2 import OAuth2PasswordRequestForm

router = APIRouter(
    tags=["auth"]
)

@router.post("/login", response_model=schemas.Token)
def login_user(db: database.SessionLocal, user: OAuth2PasswordRequestForm = Depends()):
    db_user = db.exec(select(models.User).where(models.User.email == user.username)).first()
    if not db_user or not utils.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_token({"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}