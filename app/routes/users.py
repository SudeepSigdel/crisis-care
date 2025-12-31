from fastapi import HTTPException, status, APIRouter, Depends
from .. import models, schemas, utils, database, oauth2

router = APIRouter(
    tags=["user"]
)

@router.post("/register", response_model=schemas.UserOut)
async def register_user(user: schemas.UserCreate, db: database.SessionLocal):
    valid_roles = ["user", "volunteer"]
    if user.role not in valid_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role selected")

    hashed_password = utils.get_password_hash(user.password)
    db_user = models.User(firstname=user.firstname, lastname=user.lastname, email=user.email, mobile_number=user.mobile_number, role = user.role, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

@router.get("/users", response_model=schemas.UserOut)
def get_current_user_details(current_user = Depends(oauth2.get_current_user)):
    user = current_user
    return user