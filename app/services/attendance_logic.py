from datetime import datetime
from app.services.face_matcher import cosine_similarity
from app.services.face_embedder import get_embedding, get_all_embeddings
from app.crud.attendance_crud import AttendanceCRUD
from app.crud.student_crud import StudentCRUD

THRESHOLD = 0.6

attendance_crud = AttendanceCRUD()
student_crud = StudentCRUD()


def process_attendance(face_image, student_embeddings):
    embedding = get_embedding(face_image)
    if embedding is None:
        return "No face embedding found"

    best_score = 0
    best_student_id = None

    # find best match
    for student_id, saved_embedding in student_embeddings.items():
        score = cosine_similarity(embedding, saved_embedding)
        if score > best_score:
            best_score = score
            best_student_id = student_id

    if best_score < THRESHOLD:
        return "Unknown face detected"

    today = datetime.now()

    # already marked?
    if attendance_crud.check_attendance(best_student_id, today):
        return f"{best_student_id} already marked"

    # fetch student details
    student = student_crud.get_student_by_id(best_student_id)
    student_name = student["name"] if student else best_student_id

    attendance_crud.mark_attendance({
        "student_id": best_student_id,
        "name": student_name,
        "date": today,
        "status": "Present"
    })

    return f"Attendance marked for {student_name or best_student_id}"


def process_multiple_faces(face_image, student_embeddings):
    """
    Process multiple faces in an image and match them against student embeddings
    """
    all_embeddings = get_all_embeddings(face_image)

    if not all_embeddings:
        return [{
            "status": "error",
            "message": "No faces detected in image"
        }]

    results = []
    today = datetime.now()

    for idx, (embedding, bbox) in enumerate(all_embeddings, start=1):
        best_score = 0
        best_student_id = None

        # match face with students
        for student_id, saved_embedding in student_embeddings.items():
            score = cosine_similarity(embedding, saved_embedding)
            if score > best_score:
                best_score = score
                best_student_id = student_id

        face_result = {
            "face_number": idx,
            "bbox": bbox,
            "confidence": float(best_score)
        }

        if best_score < THRESHOLD:
            face_result["status"] = "unknown"
            face_result["message"] = "Unknown face - not in database"
            results.append(face_result)
            continue

        # recognized student
        student = student_crud.get_student_by_id(best_student_id)
        student_name = student["name"] if student else best_student_id

        face_result.update({
            "student_id": best_student_id,
            "name": student_name,
            "status": "recognized"
        })

        already_marked = attendance_crud.check_attendance(best_student_id, today)
        face_result["already_marked"] = already_marked

        if already_marked:
            face_result["message"] = f"{student_name or best_student_id} already marked today"
        else:
            try:
                attendance_crud.mark_attendance({
                    "student_id": best_student_id,
                    "student_name": student_name,
                    "date": today,
                    "status": "Present"
                })
                face_result["message"] = f"Attendance marked for {student_name or best_student_id}"
            except Exception as e:
                face_result["message"] = f"DB error for {best_student_id}: {str(e)}"

        results.append(face_result)

    return results
