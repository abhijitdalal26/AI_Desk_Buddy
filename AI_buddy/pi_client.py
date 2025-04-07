import socket
import time
import logging
import os
import random
import pygame
from real_time_face_recognition.src.face_recognizer import detect_face_once  # Updated import
from gtts_voice_service import GTTSVoiceService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Songs directory at the same level as pi_client.py
SONGS_DIR = os.path.join(os.path.dirname(__file__), "songs")

def connect_to_server(host='192.168.84.248', port=65432):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    return client_socket

def play_random_song():
    """Play a random song from the songs directory."""
    try:
        # Get list of audio files in the songs directory
        song_files = [f for f in os.listdir(SONGS_DIR) if f.endswith(('.mp3', '.wav'))]
        if not song_files:
            logger.warning("No songs found in the directory.")
            return
        
        # Pick a random song
        song_path = os.path.join(SONGS_DIR, random.choice(song_files))
        logger.info(f"Playing song: {song_path}")
        
        # Initialize pygame mixer if not already initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        # Load and play the song
        pygame.mixer.music.load(song_path)
        pygame.mixer.music.play()
        
        # Wait for the song to finish playing
        while pygame.mixer.music.get_busy():
            time.sleep(1)
    except Exception as e:
        logger.error(f"Error playing song: {e}")

def main():
    # Connect to the laptop server
    client_socket = connect_to_server()
    
    # Perform face recognition and send the name
    name, confidence = detect_face_once(timeout=5.0)
    logger.info(f"Detected: {name} with confidence {confidence:.1f}%")
    client_socket.sendall(f"NAME:{name}".encode())
    
    # Initialize GTTSVoiceService
    voice_service = GTTSVoiceService(lang="en", slow=False, sentence_buffer_size=3)
    voice_service.start()
    time.sleep(1)  # Ensure TTS service is initialized
    
    # Receive and speak the greeting
    data = client_socket.recv(1024).decode()
    if data.startswith("TTS:"):
        greeting = data.replace("TTS:", "", 1).strip()
        if greeting:
            logger.info(f"Speaking greeting: '{greeting}'")
            voice_service.speak_token(greeting)
    
    # Start input loop
    try:
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                client_socket.sendall("INPUT:exit".encode())
                break
            
            # Check if the input contains the word "song"
            if "song" in user_input.lower():
                logger.info("Detected 'song' in input, playing a random song.")
                play_random_song()
            else:
                # Send input to laptop for LLM processing
                client_socket.sendall(f"INPUT:{user_input}".encode())
                logger.info(f"Sent input to laptop: '{user_input}'")
                
                # Receive and speak LLM response token-by-token until TTS_END:
                while True:
                    data = client_socket.recv(1024).decode()
                    if not data:
                        break
                    if data.startswith("TTS:"):
                        text = data.replace("TTS:", "", 1).strip()
                        if text:
                            logger.info(f"Speaking token: '{text}'")
                            voice_service.speak_token(text)
                    elif data == "TTS_END:":
                        logger.info("End of response received")
                        break
                    else:
                        logger.warning(f"Unknown data: '{data}'")
                        break
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        voice_service.stop()
        client_socket.close()
        logger.info("Client shut down")

if __name__ == "__main__":
    main()