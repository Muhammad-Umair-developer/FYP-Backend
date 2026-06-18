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
    course_name: str = Field(..., min_length=1, description="The name of the course being added")
    course_code: str = Field(..., min_length=1, description="The code of the course being added")

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
    Create a new course following the hierarchical layout:
    Degree -> Semester -> Respective Courses.
    """
    degree = payload.degree.value
    semester = str(payload.semester)  # Convert to string to use as key in nested document
    course_name = payload.course_name.strip()
    course_code = payload.course_code.strip()
    
    if not course_name or not course_code:
        raise HTTPException(status_code=400, detail="Course name and code cannot be empty")
        
    try:
        db.subjects.update_one(
            {"degree": degree},
            {"$addToSet": {f"semesters.{semester}": {"course_name": course_name, "course_code": course_code}}},
            upsert=True
        )
        
        # Retrieve the updated record to show the updated structure
        updated_doc = db.subjects.find_one({"degree": degree}, {"_id": 0})
        
        return {
            "message": f"Course '{course_name}' ({course_code}) processed successfully for {degree} Semester {semester}",
            "degree": degree,
            "semester": payload.semester,
            "course_name": course_name,
            "course_code": course_code,
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


@router.patch("/update-name")
def update_course_name(
    degree: DegreeEnum = Query(..., description="The degree name (e.g., BSCS, BSSE, BSAI)"),
    semester: int = Query(..., ge=1, le=8, description="The semester number (1 to 8)"),
    old_course_name: str = Query(..., description="The current name of the course to be updated"),
    new_course_name: str = Query(..., description="The new name for the course"),
    current_user: str = Depends(get_current_user)
):
    """
    Manually rename a course using simple input fields (query parameters).
    """
    degree_val = degree.value
    semester_str = str(semester)
    old_course_name = old_course_name.strip()
    new_course_name = new_course_name.strip()
    
    if not old_course_name or not new_course_name:
        raise HTTPException(status_code=400, detail="Course names cannot be empty")
        
    try:
        doc = db.subjects.find_one({"degree": degree_val})
        if not doc:
            raise HTTPException(status_code=404, detail=f"No courses registered for degree {degree_val}")
            
        semesters = doc.get("semesters", {})
        subjects_list = semesters.get(semester_str, [])
        
        found = False
        updated_list = []
        for x in subjects_list:
            if isinstance(x, dict) and x.get("course_name") == old_course_name:
                updated_list.append({"course_name": new_course_name, "course_code": x.get("course_code")})
                found = True
            elif isinstance(x, str) and x == old_course_name:
                # Fallback for legacy string format
                updated_list.append(new_course_name)
                found = True
            else:
                updated_list.append(x)
                
        if not found:
            raise HTTPException(
                status_code=404, 
                detail=f"Course '{old_course_name}' not found in Semester {semester} for {degree_val}"
            )
            
        # Save back to MongoDB
        db.subjects.update_one(
            {"degree": degree_val},
            {"$set": {f"semesters.{semester_str}": updated_list}}
        )
        
        return {
            "message": f"Course '{old_course_name}' successfully updated to '{new_course_name}'",
            "degree": degree_val,
            "semester": semester,
            "old_course_name": old_course_name,
            "new_course_name": new_course_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update course name: {str(e)}")


@router.delete("")
def delete_course(
    degree: DegreeEnum = Query(..., description="The degree name (e.g., BSCS, BSSE, BSAI)"),
    semester: int = Query(..., ge=1, le=8, description="The semester number (1 to 8)"),
    course_name: str = Query(..., description="The name of the course to delete"),
    current_user: str = Depends(get_current_user)
):
    """
    Manually delete a specific course from a degree and semester's list in MongoDB.
    """
    degree_val = degree.value
    semester_str = str(semester)
    course_name = course_name.strip()
    
    if not course_name:
        raise HTTPException(status_code=400, detail="Course name cannot be empty")
        
    try:
        doc = db.subjects.find_one({"degree": degree_val})
        if not doc:
            raise HTTPException(status_code=404, detail=f"No courses registered for degree {degree_val}")
            
        semesters = doc.get("semesters", {})
        subjects_list = semesters.get(semester_str, [])
        
        found = False
        updated_list = []
        for x in subjects_list:
            if isinstance(x, dict) and x.get("course_name") == course_name:
                found = True
                continue
            elif isinstance(x, str) and x == course_name:
                found = True
                continue
            else:
                updated_list.append(x)
                
        if not found:
            raise HTTPException(
                status_code=404, 
                detail=f"Course '{course_name}' not found in Semester {semester} for {degree_val}"
            )
            
        # Update MongoDB
        db.subjects.update_one(
            {"degree": degree_val},
            {"$set": {f"semesters.{semester_str}": updated_list}}
        )
        
        return {
            "message": f"Course '{course_name}' successfully deleted from {degree_val} Semester {semester}",
            "degree": degree_val,
            "semester": semester,
            "course_name": course_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete course: {str(e)}")
