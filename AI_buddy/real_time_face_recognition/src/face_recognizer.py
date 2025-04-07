import warnings
warnings.filterwarnings('ignore', category=UserWarning)

import cv2
import numpy as np
import json
import os
import logging
import time
from picamera2 import Picamera2  # Use picamera2 for Raspberry Pi camera

# Assuming settings are stored in a separate file; adjust paths as needed
try:
    from settings.settings import CAMERA, FACE_DETECTION, PATHS
except ImportError:
    # Default settings if settings.py is not available
    CAMERA = {'width': 640, 'height': 480}
    FACE_DETECTION = {'scale_factor': 1.1, 'min_neighbors': 5, 'min_size': (30, 30)}
    PATHS = {
        'trainer_file': 'trainer.yml',
        'names_file': 'names.json',
        'cascade_file': cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    }

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_camera():
    """Initialize the Raspberry Pi camera with picamera2."""
    try:
        camera = Picamera2()
        config = camera.create_preview_configuration(main={"size": (CAMERA['width'], CAMERA['height'])})
        camera.configure(config)
        camera.start()
        logger.info("Camera initialized successfully")
        return camera
    except Exception as e:
        logger.error(f"Error initializing camera: {e}")
        return None

def load_names(filename: str) -> dict:
    """Load the names dictionary from a JSON file."""
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
    """Detect a face once using the Raspberry Pi camera and return the name and confidence."""
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        if not os.path.exists(PATHS['trainer_file']):
            logger.error("Trainer file not found. Please train the model first.")
            return "Unknown", 100.0
        
        recognizer.read(PATHS['trainer_file'])
        
        face_cascade = cv2.CascadeClassifier(PATHS['cascade_file'])
        if face_cascade.empty():
            logger.error("Error loading cascade classifier")
            return "Unknown", 100.0
        
        camera = initialize_camera()
        if camera is None:
            logger.error("Failed to initialize camera")
            return "Unknown", 100.0
        
        names = load_names(PATHS['names_file'])
        if not names:
            logger.warning("No names loaded, recognition will be limited")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Capture frame using picamera2
            frame = camera.capture_array()
            # Convert RGB (picamera2 default) to BGR for OpenCV
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=FACE_DETECTION['scale_factor'],
                minNeighbors=FACE_DETECTION['min_neighbors'],
                minSize=FACE_DETECTION['min_size']
            )
            
            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                id, confidence = recognizer.predict(gray[y:y+h, x:x+w])
                
                if confidence <= 100:
                    name = names.get(str(id), "Unknown")
                else:
                    name = "Unknown"
                
                camera.close()
                return name, confidence
            
            time.sleep(0.1)
        
        logger.info("No face detected within timeout period")
        camera.close()
        return "Unknown", 100.0
    
    except Exception as e:
        logger.error(f"An error occurred in face detection: {e}")
        if 'camera' in locals():
            camera.close()
        return "Unknown", 100.0

if __name__ == "__main__":
    name, confidence = detect_face_once(timeout=5.0)
    logger.info(f"Detected: {name} with confidence {confidence:.1f}%")