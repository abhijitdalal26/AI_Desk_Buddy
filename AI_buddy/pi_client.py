import socket
import time
import logging
import os
import random
import threading
import queue
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
        except Exception as e:
            logger.error(f"Error receiving server response: {e}")
            break

def speak_farewell(voice_service, name="friend"):
    """Speak a farewell message"""
    farewells = [
        f"Goodbye {name}! It was nice talking with you.",
        f"See you later {name}! Have a great day!",
        f"Farewell {name}! Hope to chat again soon.",
        f"Take care {name}! I enjoyed our conversation."
    ]
    farewell_msg = random.choice(farewells)
    logger.info(f"Speaking farewell: '{farewell_msg}'")
    voice_service.speak_token(farewell_msg)
    # Wait for farewell to complete
    voice_service.wait_until_done()

def main():
    # Initialize pygame mixer for sound operations
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    
    client_socket = None
    voice_service = None
    user_name = "friend"  # Default name
    
    try:
        # Connect to the laptop server
        client_socket = connect_to_server()
        
        # Perform face recognition with video display and send the name
        logger.info("Starting face detection with Picamera2 (10 seconds timeout)")
        name, confidence = detect_face_once(timeout=10.0, show_video=True)
        logger.info(f"Detected: {name} with confidence {confidence:.1f}%")
        
        if name and name.lower() != "unknown":
            user_name = name  # Save the user's name for personalized farewell
        
        # Send detected name to the server
        client_socket.sendall(f"NAME:{name}".encode())
        logger.info(f"Sent name '{name}' to server")
        
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
                if user_input.lower() in ["exit", "quit", "bye"] or "bye" in user_input.lower():
                    # Speak farewell before exiting
                    if voice_service.is_speaking():
                        voice_service.stop_speaking()
                    if music_playing:
                        stop_music()
                    
                    # Let the server know we're exiting
                    client_socket.sendall("INPUT:exit".encode())
                    
                    # Speak farewell message
                    speak_farewell(voice_service, user_name)
                    break
                
                # Check for voice speed control
                if "slow" in user_input.lower() and any(word in user_input.lower() for word in ["speak", "voice", "speed"]):
                    voice_service.set_speed("slow")
                    logger.info("Set voice to slow speed")
                    continue
                
                if "fast" in user_input.lower() and any(word in user_input.lower() for word in ["speak", "voice", "speed"]):
                    voice_service.set_speed("fast")
                    logger.info("Set voice to fast speed")
                    continue
                
                if "normal" in user_input.lower() and any(word in user_input.lower() for word in ["speak", "voice", "speed"]):
                    voice_service.set_speed("normal")
                    logger.info("Set voice to normal speed")
                    continue
                
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
                
                # Check for song request
                if "song" in user_input.lower() and "stop" not in user_input.lower():
                    logger.info("Detected 'song' in input, playing a random song.")
                    music_playing = play_random_song()
                else:
                    # Stop any current TTS or music before sending new input
                    voice_service.stop_speaking()
                    if music_playing:
                        stop_music()
                        music_playing = False
                    
                    # Send input to server
                    client_socket.sendall(f"INPUT:{user_input}".encode())
                    logger.info(f"Sent input to server: '{user_input}'")
                    
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