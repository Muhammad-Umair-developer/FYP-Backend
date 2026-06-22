from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from jose import jwt, JWTError
from passlib.context import CryptContext
import bcrypt
from app.core.database import get_collection
from app.core.security import SECRET_KEY, ALGORITHM, create_access_token

router = APIRouter()

# Setup password context with sha256_crypt to avoid passlib bcrypt issues on Windows
# Default to 2000 rounds to avoid high latency on login
pwd_context = CryptContext(
    schemes=["sha256_crypt"],
    deprecated="auto",
    sha256_crypt__default_rounds=2000
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Fallback Admin Credentials
ADMIN_EMAIL = "admin@fyp.com"
ADMIN_PASSWORD = "admin123"


# Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_super_admin: bool = False


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_super_admin: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    is_super_admin: bool = False


# Password helpers
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Check if the hash looks like a bcrypt hash ($2a$, $2b$, $2y$)
        if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# Dependency to get current user
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    users_collection = get_collection("users")
    user = users_collection.find_one({"email": email})
    if user is None:
        if email == ADMIN_EMAIL:
            return {"email": ADMIN_EMAIL, "id": "admin", "is_super_admin": True}
        raise credentials_exception

    user["id"] = str(user["_id"])
    user["is_super_admin"] = bool(user.get("is_super_admin", False))
    return user


# Endpoints
@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    users_collection = get_collection("users")
    user = users_collection.find_one({"email": form_data.username})

    if not user:
        if form_data.username == ADMIN_EMAIL and form_data.password == ADMIN_PASSWORD:
            access_token = create_access_token(data={
                "sub": form_data.username,
                "is_super_admin": True
            })
            return {"access_token": access_token, "token_type": "bearer"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Automatically upgrade slow hashes (535,000 rounds) to faster hashes (2000 rounds)
    if "rounds=535000" in user.get("password", ""):
        try:
            new_hash = get_password_hash(form_data.password)
            users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"password": new_hash}}
            )
        except Exception:
            pass

    access_token = create_access_token(data={
        "sub": user["email"],
        "is_super_admin": bool(user.get("is_super_admin", False))
    })
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return login_for_access_token(form_data)


@router.get("/users", response_model=List[UserResponse])
def get_users(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action. Super Admin privileges required."
        )

    users_collection = get_collection("users")
    users = list(users_collection.find())
    
    response_users = []
    for user in users:
        response_users.append(UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            is_super_admin=bool(user.get("is_super_admin", False))
        ))
        
    return response_users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    current_user: dict = Depends(get_current_user)
):
    if not current_user.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action. Super Admin privileges required."
        )

    users_collection = get_collection("users")

    # Check if user already exists
    if users_collection.find_one({"email": user_in.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user_in.password)
    user_dict = {
        "email": user_in.email,
        "password": hashed_password,
        "is_super_admin": user_in.is_super_admin
    }
    result = users_collection.insert_one(user_dict)

    return UserResponse(
        id=str(result.inserted_id),
        email=user_in.email,
        is_super_admin=user_in.is_super_admin
    )


@router.put("/users/{email}", response_model=UserResponse)
def update_user(
    email: str,
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    if email == ADMIN_EMAIL and current_user.get("email") != ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the super admin account itself can update its profile details."
        )

    users_collection = get_collection("users")
    user = users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    update_data = {}
    if user_update.email is not None:
        existing_user = users_collection.find_one({"email": user_update.email})
        if existing_user and existing_user["email"] != email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        update_data["email"] = user_update.email

    if user_update.password is not None:
        update_data["password"] = get_password_hash(user_update.password)

    if user_update.is_super_admin is not None:
        if not current_user.get("is_super_admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Admins can update privilege levels"
            )
        update_data["is_super_admin"] = user_update.is_super_admin

    if not update_data:
        return UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            is_super_admin=bool(user.get("is_super_admin", False))
        )

    users_collection.update_one({"email": email}, {"$set": update_data})

    updated_user = users_collection.find_one({"email": update_data.get("email", email)})
    return UserResponse(
        id=str(updated_user["_id"]),
        email=updated_user["email"],
        is_super_admin=bool(updated_user.get("is_super_admin", False))
    )


@router.delete("/users/{email}", status_code=status.HTTP_200_OK)
def delete_user(
    email: str,
    current_user: dict = Depends(get_current_user)
):
    if email == ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The primary admin account cannot be deleted."
        )

    users_collection = get_collection("users")
    user = users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    users_collection.delete_one({"email": email})
    return {"detail": "User deleted successfully"}


# Seed Super Admin
def seed_super_admin():
    users_collection = get_collection("users")
    admin = users_collection.find_one({"email": ADMIN_EMAIL})
    if not admin:
        hashed_password = get_password_hash(ADMIN_PASSWORD)
        users_collection.insert_one({
            "email": ADMIN_EMAIL,
            "password": hashed_password,
            "is_super_admin": True
        })
    elif "rounds=535000" in admin.get("password", ""):
        # Upgrade admin hash if it's using the old slow rounds configuration
        hashed_password = get_password_hash(ADMIN_PASSWORD)
        users_collection.update_one(
            {"email": ADMIN_EMAIL},
            {"$set": {"password": hashed_password}}
        )


# Run seeding on startup/import
seed_super_admin()




