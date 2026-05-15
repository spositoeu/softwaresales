# users/users.py
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI()


class User(BaseModel):
    id: int = Field(default_factory=lambda: 1)
    username: str = Field(..., min_length=3, max_length=50, regex=r"^[a-zA-Z0-9_]+$")
    email: str = Field(..., min_length=5, max_length=100, regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8, max_length=200)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)


@app.post("/api/users/register", status_code=status.HTTP_201_CREATED)
def register_user(user: User):
    # In a real application, you would hash the password here and store
    # the user data in a database.
    print(f"User registered: {user}")
    return user