import socket
import time
import logging
import os
import queue
import random
import threading
import pygame
import cv2
from real_time_face_recognition.src.face_recognizer import detect_face_once
from gtts_voice_service import GTTSVoiceService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Songs directory at the same level as pi_client.py
SONGS_DIR = os.path.join(os.path.dirname(__file__), "songs")

def connect_to_server(host='192.168.143.248', port=65432):
    """Connect to the laptop server"""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        logger.info(f"Connected to server at {host}:{port}")
        return client_socket
    except Exception as e:
        logger.error(f"Failed to connect to server: {e}")
        raise

def reconnect_to_server(host='192.168.143.248', port=65432, max_attempts=3):
    """Try to reconnect to the server with multiple attempts"""
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Reconnection attempt {attempt}/{max_attempts}")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            logger.info(f"Reconnected to server at {host}:{port}")
            return client_socket
        except Exception as e:
            logger.error(f"Reconnection attempt {attempt} failed: {e}")
            time.sleep(2)  # Wait before retrying
    return None

def play_random_song():
    """Play a random song from the songs directory."""
    try:
        song_files = [f for f in os.listdir(SONGS_DIR) if f.endswith(('.mp3', '.wav'))]
        if not song_files:
            logger.warning("No songs found in the directory.")
            return False
        
        song_path = os.path.join(SONGS_DIR, random.choice(song_files))
        logger.info(f"Playing song: {song_path}")
        
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        pygame.mixer.music.load(song_path)
        pygame.mixer.music.play()
        return True
    except Exception as e:
        logger.error(f"Error playing song: {e}")
        return False

def stop_music():
    """Stop any currently playing music"""
    if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
        logger.info("Music playback stopped")
        return True
    return False

def input_listener(running_event, input_queue):
    """Thread to listen for user input without blocking main program flow"""
    while running_event.is_set():
        try:
            user_input = input().strip()
            input_queue.put(user_input)
        except EOFError:
            break
        except Exception as e:
            logger.error(f"Input error: {e}")
            break

def process_server_response(client_socket, voice_service, stop_event):
    """Process server responses and speak them until completion or interruption"""
    try:
        while not stop_event.is_set():
            try:
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
            except socket.timeout:
                logger.warning("Socket timeout, retrying...")
                continue
            except ConnectionResetError:
                logger.error("Connection was reset by the server")
                break
    except Exception as e:
        logger.error(f"Error in response processing: {e}")
    finally:
        logger.info("Response processing completed")

def main():
    # Initialize pygame mixer for sound operations
    if not pygame.mixer.get_init():
        pygame.mixer.init()
        pygame.mixer.music.set_volume(0.7)  # Set default volume to 70%
    
    client_socket = None
    voice_service = None
    
    try:
        # Connect to the laptop server
        client_socket = connect_to_server()
        
        # Perform face recognition with video display and send the name
        logger.info("Starting face detection with Picamera2 (10 seconds timeout)")
        name, confidence = detect_face_once(timeout=10.0, show_video=True)
        logger.info(f"Detected: {name} with confidence {confidence:.1f}%")
        
        # Send detected name to the server
        client_socket.sendall(f"NAME:{name}".encode())
        logger.info(f"Sent name '{name}' to server")
        
        # Initialize GTTSVoiceService
        voice_service = GTTSVoiceService(lang="en", slow=False, sentence_buffer_size=3)
        voice_service.start()
        time.sleep(1)  # Ensure TTS service is initialized
        
        # Add a local greeting if name was detected with high confidence
        if name != "Unknown" and confidence > 85:
            voice_service.speak_token(f"Hello {name}! Nice to see you again.")
        elif name == "Unknown":
            voice_service.speak_token("Hello there! I don't think we've met before.")
        else:
            voice_service.speak_token("Hello! How can I help you today?")
        
        # Receive and speak the greeting from server
        data = client_socket.recv(1024).decode()
        if data.startswith("TTS:"):
            greeting = data.replace("TTS:", "", 1).strip()
            if greeting:
                logger.info(f"Speaking greeting: '{greeting}'")
                voice_service.speak_token(greeting)
        
        # Setup async input listener
        running = threading.Event()
        running.set()
        input_queue = queue.Queue()
        input_thread = threading.Thread(target=input_listener, args=(running, input_queue))
        input_thread.daemon = True
        input_thread.start()
        
        music_playing = False
        
        # Print initial prompt
        print("\nYou: ", end="", flush=True)
        
        # Main interaction loop
        while True:
            # Check for user input (non-blocking)
            user_input = None
            try:
                user_input = input_queue.get_nowait()
                # Print a new prompt after processing this input
                print("\nYou: ", end="", flush=True)
            except queue.Empty:
                pass
            
            if user_input:
                # Check for exit commands
                if user_input.lower() in ["exit", "quit", "bye"] or "ok bye" in user_input.lower():
                    # Say goodbye before exiting
                    voice_service.speak_token("Goodbye! It was nice talking with you.")
                    voice_service.wait_until_done()  # Wait for goodbye to finish speaking
                    client_socket.sendall("INPUT:exit".encode())
                    break
                
                # Check for stop commands
                if any(command in user_input.lower() for command in ["stop", "stop speaking", "shut up"]):
                    if voice_service.is_speaking():
                        voice_service.stop_speaking()
                        logger.info("Stopped TTS playback")
                        continue
                
                # Check for stop music commands
                if any(command in user_input.lower() for command in ["stop song", "stop music", "stop playing"]):
                    if stop_music():
                        music_playing = False
                        logger.info("Stopped music playback")
                        continue
                
                # Check for volume control commands
                elif any(command in user_input.lower() for command in ["volume up", "louder"]):
                    current_volume = pygame.mixer.music.get_volume()
                    new_volume = min(1.0, current_volume + 0.1)
                    pygame.mixer.music.set_volume(new_volume)
                    voice_service.speak_token(f"Volume increased to {int(new_volume * 100)}%")
                    continue
                elif any(command in user_input.lower() for command in ["volume down", "quieter"]):
                    current_volume = pygame.mixer.music.get_volume()
                    new_volume = max(0.0, current_volume - 0.1)
                    pygame.mixer.music.set_volume(new_volume)
                    voice_service.speak_token(f"Volume decreased to {int(new_volume * 100)}%")
                    continue
                
                # Check for song request
                elif "song" in user_input.lower() and "stop" not in user_input.lower():
                    logger.info("Detected 'song' in input, playing a random song.")
                    music_playing = play_random_song()
                else:
                    # Stop any current TTS before sending new input
                    voice_service.stop_speaking()
                    
                    # Give immediate feedback
                    voice_service.speak_token("Let me think about that...")
                    
                    # Send input to server
                    try:
                        client_socket.sendall(f"INPUT:{user_input}".encode())
                        logger.info(f"Sent input to server: '{user_input}'")
                    except ConnectionError:
                        logger.error("Connection lost while sending input")
                        voice_service.speak_token("I'm having trouble connecting to the server. Let me try to reconnect.")
                        client_socket = reconnect_to_server()
                        if client_socket:
                            voice_service.speak_token("Connection restored!")
                            continue
                        else:
                            voice_service.speak_token("Sorry, I couldn't reconnect to the server. Please restart me.")
                            break
                    
                    # Stop feedback message
                    voice_service.stop_speaking()
                    
                    # Process server response
                    stop_response = threading.Event()
                    response_thread = threading.Thread(
                        target=process_server_response,
                        args=(client_socket, voice_service, stop_response)
                    )
                    response_thread.daemon = True
                    response_thread.start()
                    
                    # Wait for response to complete or be interrupted
                    response_thread.join()
            
            # Sleep to avoid high CPU usage
            time.sleep(0.1)
            
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        running.clear()  # Signal input thread to stop
        if voice_service:
            voice_service.stop()
        if client_socket:
            client_socket.close()
        cv2.destroyAllWindows()  # Ensure all OpenCV windows are closed
        logger.info("Client shut down")

if __name__ == "__main__":
    main()