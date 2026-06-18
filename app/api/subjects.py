from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from enum import Enum
from app.core.database import db

router = APIRouter()

class DegreeEnum(str, Enum):
    BSCS = "BSCS"
    BSSE = "BSSE"
    BSAI = "BSAI"

class SubjectCreateRequest(BaseModel):
    degree: DegreeEnum = Field(..., description="The degree name, strictly restricted to values like BSCS, BSSE, BSAI")
    semester: int = Field(..., ge=1, le=8, description="The semester number (1 to 8)")
    subject_name: str = Field(..., min_length=1, description="The name of the subject being added")

@router.post("/create")
def create_subject(payload: SubjectCreateRequest):
    """
    Create a new subject following the hierarchical layout:
    Degree -> Semester -> Respective Subjects.
    """
    degree = payload.degree.value
    semester = str(payload.semester)  # Convert to string to use as key in nested document
    subject_name = payload.subject_name.strip()
    
    if not subject_name:
        raise HTTPException(status_code=400, detail="Subject name cannot be empty")
        
    try:
        # Use $addToSet to add the subject_name to the list of subjects for this degree and semester.
        # This automatically prevents duplicate subject names within the same semester,
        # and dynamically structures the document hierarchically:
        # {
        #   "degree": "BSCS",
        #   "semesters": {
        #     "1": ["Programming Fundamentals", "Calculus"],
        #     "2": ["Object Oriented Programming"]
        #   }
        # }
        db.subjects.update_one(
            {"degree": degree},
            {"$addToSet": {f"semesters.{semester}": subject_name}},
            upsert=True
        )
        
        # Retrieve the updated record to show the updated structure
        updated_doc = db.subjects.find_one({"degree": degree}, {"_id": 0})
        
        return {
            "message": f"Subject '{subject_name}' processed successfully for {degree} Semester {semester}",
            "degree": degree,
            "semester": payload.semester,
            "subject_name": subject_name,
            "updated_structure": updated_doc
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save subject hierarchy: {str(e)}"
        )
