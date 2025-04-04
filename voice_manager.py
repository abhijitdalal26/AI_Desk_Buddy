"""
VoiceManager - Handles text-to-speech conversion using Google Text-to-Speech (gTTS)
"""
import os
import queue
import threading
import time
import tempfile
import pygame
from gtts import gTTS
from io import BytesIO

class VoiceManager:
    def __init__(self, lang="en", slow=False, sentence_buffer_size=3):
        """Initialize the voice manager.
        
        Args:
            lang: Language code for gTTS
            slow: Whether to speak slower
            sentence_buffer_size: Number of sentences to buffer before speaking
        """
        self.lang = lang
        self.slow = slow
        self.sentence_buffer_size = sentence_buffer_size
        
        self.text_queue = queue.Queue()  # Queue for text chunks to be spoken
        self.audio_queue = queue.Queue()  # Queue for audio files to be played
        self.active = False
        self.current_buffer = ""  # Buffer for accumulating tokens
        
        # Initialize audio playback system
        pygame.mixer.init()
        
        # Create a temporary directory for audio files
        self.temp_dir = tempfile.mkdtemp()
        
        # Set sentence-ending punctuation
        self.sentence_endings = ".!?"
    
    def start(self):
        """Start the voice manager threads."""
        self.active = True
        
        # Start the text-to-speech processing thread
        self.tts_thread = threading.Thread(target=self._tts_worker)
        self.tts_thread.daemon = True
        self.tts_thread.start()
        
        # Start the audio playback thread
        self.playback_thread = threading.Thread(target=self._playback_worker)
        self.playback_thread.daemon = True
        self.playback_thread.start()
        
        print("Voice Manager started successfully.")
    
    def stop(self):
        """Stop the voice manager."""
        self.active = False
        
        # Clear the queues
        while not self.text_queue.empty():
            self.text_queue.get()
        
        while not self.audio_queue.empty():
            audio_file = self.audio_queue.get()
            if os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                except:
                    pass
            
        # Wait for any currently playing audio to finish
        while pygame.mixer.get_busy():
            time.sleep(0.1)
            
        # Clean up temporary directory
        for f in os.listdir(self.temp_dir):
            try:
                os.remove(os.path.join(self.temp_dir, f))
            except:
                pass
                
        try:
            os.rmdir(self.temp_dir)
        except:
            pass
            
        print("Voice Manager stopped.")
    
    def speak_token(self, token):
        """Add a token to be spoken.
        
        Args:
            token: Text token to be converted to speech
        """
        # Add the token to the queue to be processed
        self.text_queue.put(token)
    
    def _tts_worker(self):
        """Worker thread for TTS processing."""
        try:
            sentence_count = 0
            
            while self.active:
                try:
                    # Get tokens from the queue with a timeout
                    token = self.text_queue.get(timeout=0.1)
                    
                    # Add to buffer
                    self.current_buffer += token
                    
                    # Check if we have a complete sentence
                    if any(ending in token for ending in self.sentence_endings):
                        sentence_count += 1
                    
                    # Check if buffer is large enough to process
                    if sentence_count >= self.sentence_buffer_size or len(self.current_buffer) > 200:
                        if self.current_buffer.strip():
                            self._process_text_to_speech(self.current_buffer)
                        self.current_buffer = ""
                        sentence_count = 0
                        
                    self.text_queue.task_done()
                    
                except queue.Empty:
                    # If no new tokens for a while and buffer has content, send it
                    if self.current_buffer and self.current_buffer.strip():
                        self._process_text_to_speech(self.current_buffer)
                        self.current_buffer = ""
                        sentence_count = 0
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"TTS worker error: {e}")
            self.active = False
    
    def _process_text_to_speech(self, text):
        """Convert text to speech and queue for playback.
        
        Args:
            text: Text to be converted to speech
        """
        try:
            # Clean up the text (remove multiple spaces, etc.)
            text = ' '.join(text.split())
            
            if not text:
                return
                
            # Create a temporary file for the audio
            temp_file = os.path.join(self.temp_dir, f"speech_{time.time()}.mp3")
            
            # Generate speech
            tts = gTTS(text=text, lang=self.lang, slow=self.slow)
            tts.save(temp_file)
            
            # Add to audio queue for playback
            self.audio_queue.put(temp_file)
            
        except Exception as e:
            print(f"Error converting text to speech: {e}")
    
    def _playback_worker(self):
        """Worker thread for audio playback."""
        try:
            while self.active:
                try:
                    # Get audio file from the queue with a timeout
                    audio_file = self.audio_queue.get(timeout=0.5)
                    
                    if os.path.exists(audio_file):
                        # Play the audio file
                        pygame.mixer.music.load(audio_file)
                        pygame.mixer.music.play()
                        
                        # Wait for playback to finish
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.1)
                            if not self.active:
                                break
                        
                        # Delete the temporary file
                        try:
                            os.remove(audio_file)
                        except:
                            pass
                            
                    self.audio_queue.task_done()
                    
                except queue.Empty:
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"Playback worker error: {e}")
            self.active = False
    
    def process_final_buffer(self):
        """Process any remaining text in the buffer."""
        if self.current_buffer and self.current_buffer.strip():
            self._process_text_to_speech(self.current_buffer)
            self.current_buffer = ""
            
    def wait_until_done(self):
        """Wait until all queued text has been spoken."""
        # Wait for the text queue to be empty
        while not self.text_queue.empty():
            time.sleep(0.1)
            
        # Process any remaining buffered text
        self.process_final_buffer()
            
        # Wait for the audio queue to be empty
        while not self.audio_queue.empty():
            time.sleep(0.1)
            
        # Wait for the last audio to finish playing
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)