import warnings
warnings.filterwarnings('ignore', category=UserWarning)

import cv2
import numpy as np
import json
import os
import logging
from .settings.settings import CAMERA, FACE_DETECTION, PATHS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_camera(camera_index: int = 0) -> cv2.VideoCapture:
    """
    Initialize the camera with error handling.
    Returns:
        cv2.VideoCapture: Initialized camera object
    """
    try:
        cam = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)  # Required for Bullseye
        if not cam.isOpened():
            logger.error("Could not open Pi Camera")
            return None

        cam.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA['width'])
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA['height'])
        logger.info("Camera initialized successfully")
        return cam
    except Exception as e:
        logger.error(f"Error initializing camera: {e}")
        return None

def load_names(filename: str) -> dict:
    """
    Load name mappings from JSON file
    """
    try:
        if os.path.exists(filename):
            with open(filename, 'r') as fs:
                content = fs.read().strip()
                if content:
                    return json.loads(content)
        return {}
    except Exception as e:
        logger.error(f"Error loading names: {e}")
        return {}

if __name__ == "__main__":
    try:
        logger.info("Starting face recognition system...")

        # Initialize face recognizer
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        if not os.path.exists(PATHS['trainer_file']):
            raise ValueError("Trainer file not found. Please train the model first.")
        recognizer.read(PATHS['trainer_file'])

        # Load face cascade
        face_cascade = cv2.CascadeClassifier(PATHS['cascade_file'])
        if face_cascade.empty():
            raise ValueError("Error loading cascade classifier")

        # Initialize camera
        cam = initialize_camera(CAMERA['index'])
        if cam is None:
            raise ValueError("Failed to initialize camera")

        # Load name mappings
        names = load_names(PATHS['names_file'])
        if not names:
            logger.warning("No names loaded; recognition will be limited")

        logger.info("Press 'ESC' to exit.")
        
        while True:
            ret, img = cam.read()
            if not ret:
                logger.warning("Failed to grab frame")
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=FACE_DETECTION['scale_factor'],
                minNeighbors=FACE_DETECTION['min_neighbors'],
                minSize=FACE_DETECTION['min_size']
            )

            for (x, y, w, h) in faces:
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)

                id, confidence = recognizer.predict(gray[y:y+h, x:x+w])

                if confidence <= 100:
                    name = names.get(str(id), "Unknown")
                    confidence_text = f"{confidence:.1f}%"
                else:
                    name = "Unknown"
                    confidence_text = f"{confidence:.1f}%"

                cv2.putText(img, name, (x+5, y-5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(img, confidence_text, (x+5, y+h-5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 1)

            cv2.imshow('Face Recognition', img)

            if cv2.waitKey(1) & 0xFF == 27:  # ESC key
                break

        logger.info("Face recognition stopped.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")

    finally:
        if 'cam' in locals() and cam is not None:
            cam.release()
        cv2.destroyAllWindows()
