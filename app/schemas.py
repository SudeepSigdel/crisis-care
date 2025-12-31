from datetime import datetime
from sqlmodel import SQLModel
from pydantic import EmailStr
from typing import Optional

class UserBase(SQLModel):
    email: str

class UserCreate(SQLModel):
    firstname: str
    lastname: str
    email: EmailStr
    mobile_number: str
    role: Optional[str] = "user"
    password: str

class UserLogin(SQLModel):
    email: str
    password: str


class Token(SQLModel):
    access_token: str
    token_type: str

class TokenData(SQLModel):
    email: str | None = None

class RequestCreate(SQLModel):
    title: str
    description: str
    request_type: str
    location_lat: float
    location_lon: float

class RequestResponse(SQLModel):
    id: int
    title: str
    description: str
    request_type: str
    location_lat: float
    location_lon: float
    is_confirmed: bool


class ResourceCreate(SQLModel):
    resource_type: str
    description: str
    location_lat: float
    location_lon: float

class ResourceResponse(SQLModel):
    id: int
    resource_type: str
    location_lat: float
    location_lon: float

class RequestUpdate(SQLModel):
    is_confirmed: bool


class MessageSchema(SQLModel):
    subject: str
    message: str
    recipient_email: str
    body: str

class UserOut(SQLModel):
    firstname: str
    lastname: str
    email: EmailStr
    mobile_number: str
    role: str
    created_at: datetime
    disabled: bool