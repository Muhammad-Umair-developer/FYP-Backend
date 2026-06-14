from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import re
from app.core.database import db

router = APIRouter()

class ClassCreateRequest(BaseModel):
    class_name: str = Field(..., description="Name of the class (e.g., BSCS-8A)")

@router.post("/create")
def create_class(payload: ClassCreateRequest):
    """
    Create a new class by dynamically creating/initializing a dedicated
    MongoDB collection for storing student records.
    """
    class_name = payload.class_name.strip()
    
    if not class_name:
        raise HTTPException(status_code=400, detail="Class name cannot be empty")
        
    # Validate the class name to prevent malicious collection names in MongoDB
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", class_name):
        raise HTTPException(
            status_code=400, 
            detail="Class name must only contain alphanumeric characters, hyphens, underscores, or periods."
        )
        
    # Check if the collection already exists
    try:
        existing_collections = db.list_collection_names()
        if class_name in existing_collections:
            return {
                "message": f"Class '{class_name}' already exists",
                "class_name": class_name,
                "collection_name": class_name,
                "created": False
            }
        
        # Dynamically create the dedicated collection in MongoDB
        db.create_collection(class_name)
        
        return {
            "message": f"Class '{class_name}' created successfully",
            "class_name": class_name,
            "collection_name": class_name,
            "created": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create class collection: {str(e)}"
        )
