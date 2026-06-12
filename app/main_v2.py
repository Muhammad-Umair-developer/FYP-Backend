"""
FastAPI main application - Production-ready Face Recognition Attendance System
All endpoints centralized and organized under /api/v1/
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from datetime import datetime
import json

# Import routers
from app.api import auth
from app.api.students_v2 import router as students_router
from app.api.attendance_v2 import router as attendance_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Face Recognition Attendance System (Production)",
    description="Comprehensive attendance management with face recognition",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# ==================== MIDDLEWARE ====================

# CORS middleware - restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZIP compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ==================== ROUTERS ====================

# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(students_router, tags=["Students (v2)"])
app.include_router(attendance_router, tags=["Attendance (v2)"])


# ==================== HEALTH CHECK ====================

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for deployment monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }


@app.get("/api/info", tags=["System"])
def api_info():
    """Get API information"""
    return {
        "name": "Face Recognition Attendance System",
        "version": "2.0.0",
        "base_url": "/api/v1",
        "documentation": "/api/docs",
        "endpoints": {
            "authentication": "/api/v1/auth",
            "students": "/api/v1/students",
            "attendance": "/api/v1/attendance"
        }
    }


# ==================== WEBSOCKET - LIVE CAMERA ====================

class ConnectionManager:
    """Manage WebSocket connections for live camera feed"""
    def __init__(self):
        self.active_connections = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_personal(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)


manager = ConnectionManager()


@app.websocket("/ws/camera/{session_id}")
async def websocket_camera(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for live camera attendance
    
    Client should send:
    {
        "type": "frame",
        "data": base64_encoded_image
    }
    
    Server responds with:
    {
        "type": "match_result",
        "matches": [...],
        "marked": count
    }
    """
    await manager.connect(websocket, session_id)
    
    try:
        import cv2
        import numpy as np
        import base64
        from app.services.face_embedder import get_embedding, get_all_embeddings
        from app.services.face_matcher import cosine_similarity
        from app.crud.student_crud import StudentCRUD
        from app.crud.attendance_crud_v2 import AttendanceCRUD
        from app.core.config import EMBEDDINGS_DIR
        import os
        
        student_crud = StudentCRUD()
        attendance_crud = AttendanceCRUD()
        
        # Load embeddings
        EMBEDDINGS_FILE = os.path.join(EMBEDDINGS_DIR, "student_embeddings.npy")
        if not os.path.exists(EMBEDDINGS_FILE):
            await websocket.send_json({"type": "error", "message": "Embeddings not found"})
            return
        
        data_embeddings = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
        student_embeddings = dict(zip(data_embeddings["student_ids"], data_embeddings["embeddings"]))
        
        marked_today = set()
        THRESHOLD = 0.6
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "frame":
                try:
                    # Decode base64 image
                    img_data = base64.b64decode(data["data"])
                    img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
                    
                    if img is None:
                        continue
                    
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    all_embeddings = get_all_embeddings(img_rgb)
                    
                    matches = []
                    newly_marked = 0
                    
                    for embedding, bbox in all_embeddings:
                        best_score = 0
                        best_student_id = None
                        
                        for s_id, s_emb in student_embeddings.items():
                            score = cosine_similarity(embedding, s_emb)
                            if score > best_score:
                                best_score = score
                                best_student_id = s_id
                        
                        student_name = None
                        if best_student_id:
                            student = student_crud.get_student_by_id(best_student_id)
                            student_name = student["name"] if student else best_student_id
                        
                        if best_score >= THRESHOLD:
                            already_marked = best_student_id in marked_today
                            
                            if not already_marked and not attendance_crud.check_attendance(best_student_id, datetime.utcnow()):
                                attendance_crud.mark_attendance({
                                    "student_id": best_student_id,
                                    "name": student_name,
                                    "date": datetime.utcnow(),
                                    "status": "Present",
                                    "confidence": float(best_score)
                                })
                                marked_today.add(best_student_id)
                                newly_marked += 1
                            
                            matches.append({
                                "student_id": best_student_id,
                                "name": student_name,
                                "confidence": float(best_score),
                                "bbox": bbox,
                                "status": "already_marked" if already_marked else "newly_marked"
                            })
                        else:
                            matches.append({
                                "student_id": "UNKNOWN",
                                "name": "UNKNOWN",
                                "confidence": float(best_score),
                                "bbox": bbox,
                                "status": "unknown"
                            })
                    
                    await manager.send_personal(session_id, {
                        "type": "match_result",
                        "timestamp": datetime.utcnow().isoformat(),
                        "faces_detected": len(matches),
                        "newly_marked": newly_marked,
                        "marked_today": len(marked_today),
                        "matches": matches
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing frame: {str(e)}")
                    await manager.send_personal(session_id, {
                        "type": "error",
                        "message": f"Error processing frame: {str(e)}"
                    })
            
            elif data.get("type") == "ping":
                await manager.send_personal(session_id, {"type": "pong"})
            
            elif data.get("type") == "end":
                break
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"Camera session {session_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(session_id)


# ==================== ROOT ENDPOINTS ====================

@app.get("/", tags=["Root"])
def root():
    """API root - redirects to documentation"""
    return {
        "message": "Face Recognition Attendance System API",
        "documentation": "/api/docs",
        "api_version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "info": "/api/info",
            "auth": "/api/v1/auth",
            "students": "/api/v1/students",
            "attendance": "/api/v1/attendance",
            "websocket": "/ws/camera/{session_id}"
        }
    }


@app.get("/api", tags=["Root"])
def api_root():
    """API root endpoint"""
    return {
        "version": "2.0.0",
        "base_path": "/api/v1",
        "modules": {
            "auth": "Authentication & JWT",
            "students": "Student management (CRUD)",
            "attendance": "Attendance tracking & reporting"
        }
    }


# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found", "path": request.url.path}
    )


@app.exception_handler(500)
async def server_error_handler(request, exc):
    logger.error(f"Server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
