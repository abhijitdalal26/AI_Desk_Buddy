"""
Configuration settings for the face recognition system
"""
import os

# Get the absolute path to the project root (two levels up from this file)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Camera settings
CAMERA = {
    'index': 0,
    'width': 640,
    'height': 480
}

# Face detection settings
FACE_DETECTION = {
    'scale_factor': 1.3,
    'min_neighbors': 5,
    'min_size': (30, 30)
}

# Training settings
TRAINING = {
    'samples_needed': 120
}

# Absolute paths for resources (based on project root)
PATHS = {
    'image_dir': os.path.join(BASE_DIR, 'images'),
    'cascade_file': os.path.join(BASE_DIR, 'haarcascade_frontalface_default.xml'),
    'names_file': os.path.join(BASE_DIR, 'names.json'),
    'trainer_file': os.path.join(BASE_DIR, 'trainer.yml')
}
