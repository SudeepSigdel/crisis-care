from sqlmodel import (
    SQLModel,
    Field,
    Relationship,
    Column,
    String,
    TIMESTAMP,
    Boolean,
    func,
)
from pydantic import EmailStr
from datetime import datetime
from typing import Optional, List

# Request table model
class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    firstname: str
    lastname: str
    email: EmailStr = Field(sa_column=Column(String, unique=True, index=True))
    mobile_number: str
    role: str | None = Field(default="User")  # user | admin | volunteer
    hashed_password: str
    disabled: bool | None = Field(default=False)
    created_at: datetime | None = Field(default_factory= datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now())
    )

    requests: List["Request"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[Request.user_id]"},
    )

    requests_volunteered: List["Request"] = Relationship(
        back_populates="volunteer",
        sa_relationship_kwargs={"foreign_keys": "[Request.volunteer_id]"},
    )

    resources: List["Resource"] = Relationship(back_populates="user")

class Request(SQLModel, table=True):
    __tablename__ = "requests"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str]
    request_type: str  # food | medical | shelter
    location_lat: float
    location_lon: float
    is_confirmed: bool = False

    user_id: int = Field(foreign_key="users.id", nullable=False)
    volunteer_id: Optional[int] = Field(foreign_key="users.id", default=None)

    created_at: datetime | None = Field(default_factory= datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now())
    )

    # Relationships
    user: "User" = Relationship(
        back_populates="requests",
        sa_relationship_kwargs={"foreign_keys": "[Request.user_id]"},
    )

    volunteer: Optional["User"] = Relationship(
        back_populates="requests_volunteered",
        sa_relationship_kwargs={"foreign_keys": "[Request.volunteer_id]"},
    )

class Resource(SQLModel, table=True):
    __tablename__ = "resources"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    resource_type: str  # water | clothes | food
    description: str | None = ""
    location_lat: float
    location_lon: float
    is_available: bool = True

    user_id: int = Field(foreign_key="users.id", nullable=False)

    created_at: datetime | None = Field(default_factory=datetime.utcnow,
        sa_column=Column(TIMESTAMP(timezone=True), server_default=func.now())
    )

    # Relationships
    user: "User" = Relationship(back_populates="resources")
