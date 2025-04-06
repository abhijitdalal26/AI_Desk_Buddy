import warnings
warnings.filterwarnings('ignore', category=UserWarning)

import cv2
import numpy as np
import json
import os
import logging
import time
from .settings.settings import CAMERA, FACE_DETECTION, PATHS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_camera(camera_index: int = 0) -> cv2.VideoCapture:
    """
    Initialize the camera with error handling
    """
    try:
        cam = cv2.VideoCapture(camera_index)
        if not cam.isOpened():
            logger.error("Could not open webcam")
            return None
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA['width'])
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA['height'])
        return cam
    except Exception as e:
        logger.error(f"Error initializing camera: {e}")
        return None

def load_names(filename: str) -> dict:
    """
    Load name mappings from JSON file
    """
    try:
        names_json = {}
        if os.path.exists(filename):
            with open(filename, 'r') as fs:
                content = fs.read().strip()
                if content:
                    names_json = json.loads(content)
        return names_json
    except Exception as e:
        logger.error(f"Error loading names: {e}")
        return {}

def detect_face_once(timeout: float = 5.0) -> tuple[str, float]:
    """
    Detect a face within a given timeout period and return the recognized name and confidence.
    
    Parameters:
        timeout (float): Maximum time in seconds to attempt face detection (default: 5.0)
    Returns:
        tuple: (name, confidence) where name is "Unknown" if not recognized or confidence > 100
    """
    try:
        # Initialize face recognizer
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        if not os.path.exists(PATHS['trainer_file']):
            logger.error("Trainer file not found. Please train the model first.")
            return "Unknown", 100.0
        
        recognizer.read(PATHS['trainer_file'])
        
        # Load face cascade classifier
        face_cascade = cv2.CascadeClassifier(PATHS['cascade_file'])
        if face_cascade.empty():
            logger.error("Error loading cascade classifier")
            return "Unknown", 100.0
        
        # Initialize camera
        cam = initialize_camera(CAMERA['index'])
        if cam is None:
            logger.error("Failed to initialize camera")
            return "Unknown", 100.0
        
        # Load names
        names = load_names(PATHS['names_file'])
        if not names:
            logger.warning("No names loaded, recognition will be limited")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Capture a frame
            ret, img = cam.read()
            if not ret:
                logger.warning("Failed to grab frame")
                time.sleep(0.1)  # Brief pause before retrying
                continue
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=FACE_DETECTION['scale_factor'],
                minNeighbors=FACE_DETECTION['min_neighbors'],
                minSize=FACE_DETECTION['min_size']
            )
            
            if len(faces) > 0:
                # Process the first detected face
                (x, y, w, h) = faces[0]
                id, confidence = recognizer.predict(gray[y:y+h, x:x+w])
                
                if confidence <= 100:
                    name = names.get(str(id), "Unknown")
                else:
                    name = "Unknown"
                
                cam.release()
                cv2.destroyAllWindows()
                return name, confidence
            
            # Small delay to avoid overloading CPU
            time.sleep(0.1)
        
        # Timeout reached, no face detected
        logger.info("No face detected within timeout period")
        cam.release()
        cv2.destroyAllWindows()
        return "Unknown", 100.0
    
    except Exception as e:
        logger.error(f"An error occurred in face detection: {e}")
        if 'cam' in locals():
            cam.release()
        cv2.destroyAllWindows()
        return "Unknown", 100.0

if __name__ == "__main__":
    name, confidence = detect_face_once(timeout=5.0)
    logger.info(f"Detected: {name} with confidence {confidence:.1f}%")