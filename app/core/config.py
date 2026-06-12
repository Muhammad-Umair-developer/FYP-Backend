import os
from dotenv import load_dotenv

load_dotenv()


MONGO_URI=os.getenv("MONGO_URI","mongodb://localhost:27017")
DB_NAME=os.getenv("DB_NAME","attendance_db")
EMBEDDINGS_DIR=os.getenv("EMBEDDINGS_DIR","datasets/embeddings")

# Face Recognition Settings
RECOGNITION_THRESHOLD = float(os.getenv("RECOGNITION_THRESHOLD", "0.6"))
EMBEDDING_DIMENSION = 512

# API Settings
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg"}

# Pagination
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500

# Default Collections
DEFAULT_ATTENDANCE_COLLECTION = os.getenv("ATTENDANCE_COLLECTION", "BSCS_8B")
DEFAULT_STUDENT_COLLECTION = os.getenv("STUDENT_COLLECTION", "students")