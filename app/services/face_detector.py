from mtcnn import MTCNN
import cv2
import numpy as np
import time

detector=MTCNN()
last_processed_time = 0.0


def detect_faces(image_input):
    """
    Detect faces from image path or numpy array
    Returns detection information with bounding boxes
    Args:
        image_input: either a file path (str) or numpy array (already in RGB)
    Returns:
        List of detections with bbox and confidence
    """
    global last_processed_time
    current_time = time.time()
    if current_time - last_processed_time < 0.15:
        return None

    if isinstance(image_input, str):
        # It's a file path
        img=cv2.imread(image_input)
        img_rgb=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    elif isinstance(image_input, np.ndarray):
        # It's already a numpy array (assumed to be RGB)
        img_rgb=image_input
    else:
        raise ValueError("image_input must be a file path or numpy array")
    
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    if cv2.Laplacian(gray, cv2.CV_64F).var() < 85.0:
        return None

    if gray.mean() < 80.0:
        lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        img_rgb = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)

    results=detector.detect_faces(img_rgb)
    
    detections = []
    for r in results:
        x, y, w, h = r['box']
        # Ensure coordinates are positive
        x, y = max(0, x), max(0, y)
        x2, y2 = x + w, y + h
        
        detections.append({
            'bbox': [x, y, x2, y2],
            'confidence': r.get('confidence', 0),
            'face_region': img_rgb[y:y2, x:x2]
        })
    
    last_processed_time = current_time
    return detections



    