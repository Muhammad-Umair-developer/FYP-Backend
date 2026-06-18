from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
import re
from app.core.database import db
from app.core.security import get_current_user

router = APIRouter()

class DegreeEnum(str, Enum):
    BSCS = "BSCS"
    BSSE = "BSSE"
    BSAI = "BSAI"

class SubjectCreateRequest(BaseModel):
    degree: DegreeEnum = Field(..., description="The degree name, strictly restricted to values like BSCS, BSSE, BSAI")
    semester: int = Field(..., ge=1, le=8, description="The semester number (1 to 8)")
    subject_name: str = Field(..., min_length=1, description="The name of the subject being added")

def parse_class_name(class_name: str):
    """
    Parse degree and semester from class names like BSCS-8A, BSCS_8B, BSAI-3, etc.
    """
    match = re.match(r"^([a-zA-Z]+)[-_]?([1-8])", class_name.strip())
    if match:
        degree = match.group(1).upper()
        semester = int(match.group(2))
        return degree, semester
    return None, None

@router.post("/create")
def create_subject(payload: SubjectCreateRequest, current_user: str = Depends(get_current_user)):
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

@router.get("")
def list_subjects(
    degree: Optional[str] = Query(None, description="Degree name (e.g. BSCS)"),
    semester: Optional[int] = Query(None, ge=1, le=8, description="Semester number (1-8)"),
    class_name: Optional[str] = Query(None, description="Class name (e.g. BSCS-8A, BSCS_8B) to auto-extract degree & semester"),
    current_user: str = Depends(get_current_user)
):
    """
    Fetch all subjects registered under a specific degree and semester.
    If class_name is provided, it extracts the degree and semester dynamically.
    """
    # If class_name is provided, parse degree and semester
    if class_name:
        parsed_degree, parsed_semester = parse_class_name(class_name)
        if parsed_degree and parsed_semester:
            degree = parsed_degree
            semester = parsed_semester
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Could not parse degree and semester from class name '{class_name}'"
            )

    if not degree or semester is None:
        raise HTTPException(
            status_code=400,
            detail="Either both (degree and semester) must be provided, or class_name must be provided."
        )

    degree = degree.upper().strip()
    
    # Retrieve the subjects document
    doc = db.subjects.find_one({"degree": degree}, {"_id": 0})
    if not doc:
        return []
    
    # Return the array under semesters.<semester>
    semesters = doc.get("semesters", {})
    return semesters.get(str(semester), [])
