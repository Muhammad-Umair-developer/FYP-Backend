"""
Unified face matching service - centralized matching logic
Eliminates duplication across main.py, attendance_logic.py, and scripts
"""
from typing import List, Tuple, Dict, Optional
import numpy as np
from datetime import datetime
from app.services.face_embedder import get_embedding, get_all_embeddings
from app.services.face_matcher import cosine_similarity
from app.crud.student_crud import StudentCRUD
from app.crud.attendance_crud import AttendanceCRUD
from app.core.config import RECOGNITION_THRESHOLD

student_crud = StudentCRUD()
attendance_crud = AttendanceCRUD()


class MatchingResult:
    """Standardized matching result structure"""
    def __init__(self, student_id: str, student_name: str, confidence: float, 
                 bbox: Optional[List] = None, already_marked: bool = False):
        self.student_id = student_id
        self.student_name = student_name
        self.confidence = confidence
        self.bbox = bbox
        self.already_marked = already_marked
        self.status = "recognized" if confidence >= RECOGNITION_THRESHOLD else "unknown"
    
    def to_dict(self):
        return {
            "student_id": self.student_id,
            "name": self.student_name,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "status": self.status,
            "already_marked": self.already_marked
        }


def match_single_face(face_embedding: np.ndarray, 
                     all_student_embeddings: Dict[str, np.ndarray]) -> Tuple[str, float]:
    """
    Match a single face embedding against all student embeddings
    Returns: (best_student_id, best_score)
    """
    best_score = 0
    best_student_id = None
    
    for student_id, student_embedding in all_student_embeddings.items():
        score = cosine_similarity(face_embedding, student_embedding)
        if score > best_score:
            best_score = score
            best_student_id = student_id
    
    return best_student_id, best_score


def match_multiple_faces(face_image, all_student_embeddings: Dict[str, np.ndarray],
                        check_duplicates: bool = True, date: Optional[datetime] = None) -> List[MatchingResult]:
    """
    Match multiple faces in image against student embeddings
    
    Args:
        face_image: Image (numpy array or file path)
        all_student_embeddings: Dict of {student_id: embedding}
        check_duplicates: Whether to check if already marked today
        date: Date to check duplicates for (defaults to today)
    
    Returns:
        List of MatchingResult objects
    """
    all_embeddings = get_all_embeddings(face_image)
    
    if not all_embeddings:
        return []
    
    results = []
    if date is None:
        date = datetime.utcnow()
    
    for embedding, bbox in all_embeddings:
        best_student_id, best_score = match_single_face(embedding, all_student_embeddings)
        
        # Fetch student details
        student_name = None
        if best_student_id:
            student = student_crud.get_student_by_id(best_student_id)
            student_name = student["name"] if student else best_student_id
        
        # Check if already marked today
        already_marked = False
        if check_duplicates and best_score >= RECOGNITION_THRESHOLD:
            already_marked = attendance_crud.check_attendance(best_student_id, date) is not None
        
        result = MatchingResult(
            student_id=best_student_id or "UNKNOWN",
            student_name=student_name or "UNKNOWN",
            confidence=float(best_score),
            bbox=bbox,
            already_marked=already_marked
        )
        
        results.append(result)
    
    return results


def mark_attendance_for_matches(matches: List[MatchingResult], 
                               class_name: str = "BSCS_8B",
                               date: Optional[datetime] = None) -> Dict:
    """
    Mark attendance for matched faces
    
    Returns:
        {"marked": count, "duplicates": count, "failed": [errors]}
    """
    if date is None:
        date = datetime.utcnow()
    
    marked_count = 0
    duplicate_count = 0
    failed = []
    
    for match in matches:
        if match.status == "unknown":
            continue
        
        if match.already_marked:
            duplicate_count += 1
            continue
        
        try:
            attendance_crud.mark_attendance(
                {
                    "student_id": match.student_id,
                    "name": match.student_name,
                    "date": date,
                    "status": "Present",
                    "class": class_name,
                    "confidence": match.confidence
                }
            )
            marked_count += 1
        except Exception as e:
            failed.append({"student_id": match.student_id, "error": str(e)})
    
    return {
        "marked": marked_count,
        "duplicates": duplicate_count,
        "failed": failed
    }
