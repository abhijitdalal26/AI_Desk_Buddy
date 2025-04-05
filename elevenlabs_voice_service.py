"""
ElevenLabsVoiceService - Handles text-to-speech conversion using ElevenLabs API
"""
import os
import queue
import threading
import time
import tempfile
import pygame
import requests

class ElevenLabsVoiceService:
    def __init__(self, api_key, voice_id="21m00Tcm4TlvDq8ikWAM", model_id="eleven_monolingual_v1", 
                 stability=0.5, similarity_boost=0.5, sentence_buffer_size=3):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.sentence_buffer_size = sentence_buffer_size
        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        self.active = False
        self.current_buffer = ""
        pygame.mixer.init()
        self.temp_dir = tempfile.mkdtemp()
        self.sentence_endings = ".!?"
        self.tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        self.voices_url = "https://api.elevenlabs.io/v1/voices"
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
    
    def start(self):
        self.active = True
        self.tts_thread = threading.Thread(target=self._tts_worker)
        self.tts_thread.daemon = True
        self.tts_thread.start()
        self.playback_thread = threading.Thread(target=self._playback_worker)
        self.playback_thread.daemon = True
        self.playback_thread.start()
        try:
            self._verify_api_key()
            print("ElevenLabs Voice Service started successfully.")
        except Exception as e:
            print(f"ElevenLabs API error: {e}")
    
    def _verify_api_key(self):
        response = requests.get(self.voices_url, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"API key verification failed: {response.status_code} - {response.text}")
    
    def stop(self):
        self.active = False
        while not self.text_queue.empty():
            self.text_queue.get()
        while not self.audio_queue.empty():
            audio_file = self.audio_queue.get()
            if os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                except:
                    pass
        while pygame.mixer.get_busy():
            time.sleep(0.1)
        for f in os.listdir(self.temp_dir):
            try:
                os.remove(os.path.join(self.temp_dir, f))
            except:
                pass
        try:
            os.rmdir(self.temp_dir)
        except:
            pass
        print("ElevenLabs Voice Service stopped.")
    
    def speak_token(self, token):
        self.text_queue.put(token)
    
    def _tts_worker(self):
        sentence_count = 0
        while self.active:
            try:
                token = self.text_queue.get(timeout=0.1)
                self.current_buffer += token
                if any(ending in token for ending in self.sentence_endings):
                    sentence_count += 1
                if sentence_count >= self.sentence_buffer_size or len(self.current_buffer) > 200:
                    if self.current_buffer.strip():
                        self._process_text_to_speech(self.current_buffer)
                    self.current_buffer = ""
                    sentence_count = 0
                self.text_queue.task_done()
            except queue.Empty:
                if self.current_buffer and self.current_buffer.strip():
                    self._process_text_to_speech(self.current_buffer)
                    self.current_buffer = ""
                    sentence_count = 0
                time.sleep(0.1)
    
    def _process_text_to_speech(self, text):
        text = ' '.join(text.split())
        if not text:
            return
        temp_file = os.path.join(self.temp_dir, f"speech_{time.time()}.mp3")
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost
            }
        }
        response = requests.post(self.tts_url, json=payload, headers=self.headers)
        if response.status_code == 200:
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            self.audio_queue.put(temp_file)
        else:
            print(f"ElevenLabs API error: {response.status_code} - {response.text}")
    
    def _playback_worker(self):
        while self.active:
            try:
                audio_file = self.audio_queue.get(timeout=0.5)
                if os.path.exists(audio_file):
                    pygame.mixer.music.load(audio_file)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                        if not self.active:
                            break
                    try:
                        os.remove(audio_file)
                    except:
                        pass
                self.audio_queue.task_done()
            except queue.Empty:
                time.sleep(0.1)
    
    def process_final_buffer(self):
        if self.current_buffer and self.current_buffer.strip():
            self._process_text_to_speech(self.current_buffer)
            self.current_buffer = ""
    
    def wait_until_done(self):
        while not self.text_queue.empty():
            time.sleep(0.1)
        self.process_final_buffer()
        while not self.audio_queue.empty():
            time.sleep(0.1)
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)