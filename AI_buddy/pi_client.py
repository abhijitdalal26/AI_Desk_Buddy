import socket
import time
import logging
from real_time_face_recognition.src.face_recognizer import detect_face_once  # Assuming package structure
from gtts_voice_service import GTTSVoiceService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_server(host='192.168.84.248', port=65432):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    return client_socket

def main():
    # Connect to the laptop server
    client_socket = connect_to_server()
    
    # Perform face recognition and send the name
    name, confidence = detect_face_once(timeout=5.0)
    client_socket.sendall(f"NAME:{name}".encode())
    logger.info(f"Sent name: {name} with confidence {confidence}")
    
    # Initialize GTTSVoiceService
    voice_service = GTTSVoiceService(lang="en", slow=False, sentence_buffer_size=3)
    voice_service.start()
    
    # Listen for TTS commands from the laptop
    try:
        while True:
            data = client_socket.recv(1024).decode()
            logger.info(f"Received raw data: '{data}'")
            if data.startswith("TTS:"):
                # Strip all instances of "TTS:" and clean the text
                text = data.replace("TTS:", "").strip()
                if text:  # Ensure there's actual text to speak
                    logger.info(f"Sending to voice_service: '{text}'")
                    voice_service.speak_token(text)
            elif data.startswith("EXIT:"):
                logger.info("Received exit command")
                voice_service.stop()
                break
            else:
                logger.warning(f"Unknown command received: '{data}'")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        voice_service.stop()
        client_socket.close()
        logger.info("Client shut down")

if __name__ == "__main__":
    main()