from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta

# ================= CONFIG =================
SECRET_KEY = "CHANGE_THIS_SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# OAuth2 Password Bearer flow pointing to /auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ================= TOKEN CREATION =================
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ================= TOKEN VERIFICATION =================
def get_current_user(
    token: str = Depends(oauth2_scheme),
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return email

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
