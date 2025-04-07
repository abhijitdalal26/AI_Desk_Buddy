import os
import queue
import threading
import time
import tempfile
import pygame
from gtts import gTTS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GTTSVoiceService:
    def __init__(self, lang="en", slow=False, sentence_buffer_size=3):
        self.lang = lang
        self.slow = slow
        self.sentence_buffer_size = sentence_buffer_size
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        self.active = False
        self.current_buffer = ""
        self.temp_dir = tempfile.mkdtemp()
        self.sentence_endings = ".!?"
        self.playing = False
        self.stop_requested = False
    
    def start(self):
        self.active = True
        pygame.mixer.init()
        time.sleep(0.5)  # Add a small delay to ensure mixer is initialized
        self.tts_thread = threading.Thread(target=self._tts_worker)
        self.tts_thread.daemon = True
        self.tts_thread.start()
        self.playback_thread = threading.Thread(target=self._playback_worker)
        self.playback_thread.daemon = True
        self.playback_thread.start()
        logger.info("Google TTS Voice Service started successfully.")
    
    def stop(self):
        self.active = False
        self.stop_requested = True
        # Stop any currently playing audio
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        # Clear the queues
        self._clear_queues()
        while pygame.mixer.get_busy():
            time.sleep(0.1)
        self._cleanup_temp_files()
        logger.info("Google TTS Voice Service stopped.")
    
    def _clear_queues(self):
        """Clear all pending text and audio queues"""
        while not self.text_queue.empty():
            self.text_queue.get()
        while not self.audio_queue.empty():
            audio_file = self.audio_queue.get()
            if os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                except:
                    pass
    
    def _cleanup_temp_files(self):
        """Clean up all temporary files"""
        for f in os.listdir(self.temp_dir):
            try:
                os.remove(os.path.join(self.temp_dir, f))
            except:
                pass
        try:
            os.rmdir(self.temp_dir)
        except:
            pass
    
    def speak_token(self, token):
        logger.info(f"Received token: '{token}'")
        self.text_queue.put(token)
    
    def stop_speaking(self):
        """Stop current speech playback and clear pending speech"""
        logger.info("Stop speaking requested")
        self.stop_requested = True
        self.current_buffer = ""
        self._clear_queues()
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        time.sleep(0.1)  # Give a moment for things to clear
        self.stop_requested = False
        logger.info("Speech stopped")
    
    def is_speaking(self):
        """Check if the TTS service is currently speaking or has pending speech"""
        return (self.playing or 
                not self.text_queue.empty() or 
                not self.audio_queue.empty() or 
                bool(self.current_buffer.strip()))
    
    def _tts_worker(self):
        sentence_count = 0
        while self.active:
            try:
                if self.stop_requested:
                    time.sleep(0.1)
                    continue
                
                token = self.text_queue.get(timeout=0.1)
                self.current_buffer += token
                logger.info(f"Buffer updated: '{self.current_buffer}'")
                if any(ending in token for ending in self.sentence_endings):
                    sentence_count += 1
                if sentence_count >= self.sentence_buffer_size or len(self.current_buffer) > 200:
                    if self.current_buffer.strip():
                        logger.info(f"Converting to speech: '{self.current_buffer}'")
                        self._process_text_to_speech(self.current_buffer)
                    self.current_buffer = ""
                    sentence_count = 0
                self.text_queue.task_done()
            except queue.Empty:
                if self.current_buffer and self.current_buffer.strip() and not self.stop_requested:
                    logger.info(f"Converting final buffer to speech: '{self.current_buffer}'")
                    self._process_text_to_speech(self.current_buffer)
                    self.current_buffer = ""
                    sentence_count = 0
                time.sleep(0.1)
    
    def _process_text_to_speech(self, text):
        if self.stop_requested:
            return
        
        text = ' '.join(text.split())
        if not text:
            return
        temp_file = os.path.join(self.temp_dir, f"speech_{time.time()}.mp3")
        tts = gTTS(text=text, lang=self.lang, slow=self.slow)
        tts.save(temp_file)
        self.audio_queue.put(temp_file)
        logger.info(f"Audio file queued: {temp_file}")
    
    def _playback_worker(self):
        while self.active:
            try:
                if self.stop_requested:
                    time.sleep(0.1)
                    continue
                    
                audio_file = self.audio_queue.get(timeout=0.5)
                if os.path.exists(audio_file):
                    self.playing = True
                    pygame.mixer.music.load(audio_file)
                    pygame.mixer.music.play()
                    logger.info(f"Playing audio: {audio_file}")
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                        if not self.active or self.stop_requested:
                            pygame.mixer.music.stop()
                            break
                    try:
                        os.remove(audio_file)
                        logger.info(f"Deleted audio file: {audio_file}")
                    except:
                        pass
                    self.playing = False
                self.audio_queue.task_done()
            except queue.Empty:
                time.sleep(0.1)
    
    def process_final_buffer(self):
        if self.current_buffer and self.current_buffer.strip() and not self.stop_requested:
            logger.info(f"Processing final buffer: '{self.current_buffer}'")
            self._process_text_to_speech(self.current_buffer)
            self.current_buffer = ""
    
    def wait_until_done(self):
        while not self.text_queue.empty():
            time.sleep(0.1)
            if self.stop_requested:
                break
        self.process_final_buffer()
        while not self.audio_queue.empty():
            time.sleep(0.1)
            if self.stop_requested:
                break
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
            if self.stop_requested:
                break