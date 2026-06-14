from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import create_access_token

router = APIRouter()

# Dummy Admin (FYP Safe)
ADMIN_EMAIL = "admin@fyp.com"
ADMIN_PASSWORD = "admin123"


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == ADMIN_EMAIL and form_data.password == ADMIN_PASSWORD:
        token = create_access_token({"sub": form_data.username})
        return {
            "access_token": token,
            "token_type": "bearer"
        }

    raise HTTPException(status_code=401, detail="Invalid credentials")
