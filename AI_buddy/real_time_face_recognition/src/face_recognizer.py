# Updated face_recognizer.py using Picamera2 for Raspberry Pi 4B with Bullseye
# For real_time_face_recognition/src/face_recognizer.py

import cv2
import numpy as np
import json
import os
import logging
import time
from picamera2 import Picamera2
from .settings.settings import CAMERA, FACE_DETECTION, PATHS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def detect_face_once(timeout=10.0, show_video=True):
    """
    Detect a face and return the recognized name and confidence using Picamera2.
    Runs for the specified timeout duration or until ESC is pressed.
    
    Args:
        timeout (float): Maximum time to run face detection (in seconds)
        show_video (bool): Whether to display the video feed
        
    Returns:
        tuple: (name, confidence) where name is the recognized name or "Unknown"
               and confidence is the recognition confidence percentage
    """
    try:
        logger.info(f"Starting face detection with Picamera2, timeout: {timeout} seconds")
        
        # Initialize face recognizer
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        if not os.path.exists(PATHS['trainer_file']):
            logger.error("Trainer file not found. Please train the model first.")
            return "Unknown", 0.0
        recognizer.read(PATHS['trainer_file'])
        
        # Load face cascade
        face_cascade = cv2.CascadeClassifier(PATHS['cascade_file'])
        if face_cascade.empty():
            logger.error("Error loading cascade classifier")
            return "Unknown", 0.0
        
        # Initialize Picamera2
        picam2 = Picamera2()
        preview_config = picam2.create_preview_configuration(
            main={"format": "RGB888", "size": (CAMERA['width'], CAMERA['height'])}
        )
        picam2.configure(preview_config)
        picam2.start()
        
        # Wait a moment for the camera to stabilize
        time.sleep(0.5)
        
        # Load name mappings
        names = load_names(PATHS['names_file'])
        if not names:
            logger.warning("No names loaded; recognition will show IDs instead of names")
        
        best_name = "Unknown"
        best_confidence = 0.0
        start_time = time.time()
        frame_count = 0
        
        while (time.time() - start_time) < timeout:
            try:
                # Capture frame from Picamera2
                img = picam2.capture_array()
                frame_count += 1
                
                # Convert to grayscale for face detection
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Detect faces
                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=FACE_DETECTION['scale_factor'],
                    minNeighbors=FACE_DETECTION['min_neighbors'],
                    minSize=FACE_DETECTION['min_size']
                )
                
                # Process detected faces
                for (x, y, w, h) in faces:
                    cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    
                    # Recognize the face
                    id, confidence = recognizer.predict(gray[y:y+h, x:x+w])
                    confidence_value = 100 - confidence  # Convert to percentage
                    
                    # Track best match
                    if confidence_value > best_confidence:
                        best_confidence = confidence_value
                        best_name = names.get(str(id), f"Person_{id}")
                    
                    # Display name and confidence
                    name = names.get(str(id), f"Person_{id}") if confidence < 70 else "Unknown"
                    confidence_text = f"{confidence_value:.1f}%"
                    
                    cv2.putText(img, name, (x+5, y-5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    cv2.putText(img, confidence_text, (x+5, y+h-5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 1)
                
                # Show video if requested
                if show_video:
                    # Show remaining time countdown
                    time_left = max(0, int(timeout - (time.time() - start_time)))
                    cv2.putText(img, f"Time: {time_left}s", 
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    cv2.putText(img, f"Best: {best_name} ({best_confidence:.1f}%)", 
                                (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    
                    cv2.imshow('Face Recognition', img)
                
                # Check for ESC key (with short wait to prevent CPU usage)
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC key
                    break
                    
            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                continue
        
        logger.info(f"Face detection completed. Processed {frame_count} frames.")
        logger.info(f"Best match: {best_name} with {best_confidence:.1f}% confidence")
        
        # Cleanup
        picam2.stop()
        if show_video:
            cv2.destroyAllWindows()
        
        return best_name, best_confidence
        
    except Exception as e:
        logger.error(f"Error in face detection: {e}")
        if 'picam2' in locals():
            picam2.stop()
        cv2.destroyAllWindows()
        return "Unknown", 0.0

# For direct testing
if __name__ == "__main__":
    name, confidence = detect_face_once(timeout=10.0, show_video=True)
    print(f"Detected: {name} with confidence {confidence:.1f}%")