#!/usr/bin/env python3
import pyaudio
import numpy as np
import time
import threading
import argparse
import signal
import sys
import os

class AudioPassthrough:
    def __init__(self, input_device=None, output_device=None, rate=44100, 
                 chunk_size=1024, channels=1, format_type=pyaudio.paInt16,
                 volume=1.0, noise_gate=0.01):
        """
        Initialize audio passthrough with configurable parameters.
        
        Args:
            input_device: Index of input device (None for default)
            output_device: Index of output device (None for default)
            rate: Sample rate in Hz
            chunk_size: Number of frames per buffer
            channels: Number of audio channels (1=mono, 2=stereo)
            format_type: Audio format (default: 16-bit)
            volume: Volume multiplier (1.0 = original volume)
            noise_gate: Threshold below which audio is silenced (0-1.0)
        """
        self.p = pyaudio.PyAudio()
        self.rate = rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.format_type = format_type
        self.volume = volume
        self.noise_gate = noise_gate
        self.running = False
        self.input_stream = None
        self.output_stream = None
        self.processing_thread = None
        
        # Identify input and output devices
        self.input_device_index = self._find_device(input_device, is_input=True)
        self.output_device_index = self._find_device(output_device, is_input=False)
        
        # Sample width for volume adjustment calculations
        self.sample_width = self.p.get_sample_size(format_type)
        
    def _find_device(self, device_hint, is_input=True):
        """Find appropriate audio device based on hint or default"""
        if device_hint is not None:
            try:
                # If a number was provided, use it directly
                if isinstance(device_hint, int):
                    return device_hint
                # If a string was provided, try to find matching device
                for i in range(self.p.get_device_count()):
                    device_info = self.p.get_device_info_by_index(i)
                    if (is_input and device_info['maxInputChannels'] > 0 or
                        not is_input and device_info['maxOutputChannels'] > 0):
                        if device_hint.lower() in device_info['name'].lower():
                            return i
            except:
                pass
        
        # Use default device if no matching device found
        return None
    
    def list_devices(self):
        """List all available audio devices"""
        print("\n==== Available Audio Devices ====")
        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            input_ch = dev['maxInputChannels']
            output_ch = dev['maxOutputChannels']
            name = dev['name']
            
            if input_ch > 0:
                print(f"[IN]  Device {i}: {name}")
            if output_ch > 0:
                print(f"[OUT] Device {i}: {name}")
        print("================================\n")
    
    def start(self):
        """Start audio passthrough"""
        if self.running:
            print("Already running!")
            return
            
        try:
            # Open input stream
            self.input_stream = self.p.open(
                format=self.format_type,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.chunk_size
            )
            
            # Open output stream
            self.output_stream = self.p.open(
                format=self.format_type,
                channels=self.channels,
                rate=self.rate,
                output=True,
                output_device_index=self.output_device_index,
                frames_per_buffer=self.chunk_size
            )
            
            self.running = True
            
            # Start processing in a separate thread
            self.processing_thread = threading.Thread(target=self._process_audio)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            
            input_device_name = self.p.get_device_info_by_index(
                self.input_device_index if self.input_device_index is not None else 
                self.p.get_default_input_device_info()['index']
            )['name']
            
            output_device_name = self.p.get_device_info_by_index(
                self.output_device_index if self.output_device_index is not None else 
                self.p.get_default_output_device_info()['index']
            )['name']
            
            print(f"🎙️  Mic to speaker passthrough started.")
            print(f"Input: {input_device_name}")
            print(f"Output: {output_device_name}")
            print(f"Sample Rate: {self.rate} Hz, Channels: {self.channels}")
            print(f"Volume: {self.volume:.1f}, Noise Gate: {self.noise_gate:.3f}")
            print("Press Ctrl+C to stop.")
            
        except Exception as e:
            print(f"Error starting audio passthrough: {e}")
            self.cleanup()
            return False
        
        return True
    
    def _process_audio(self):
        """Process audio from input to output with volume control and noise gate"""
        try:
            while self.running:
                # Read audio data
                data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Apply volume adjustment and noise gate if needed
                if self.volume != 1.0 or self.noise_gate > 0:
                    # Convert bytes to numpy array for processing
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    
                    # Apply noise gate (silence audio below threshold)
                    if self.noise_gate > 0:
                        # Calculate average amplitude
                        max_value = float(np.iinfo(np.int16).max)
                        amplitude = np.abs(audio_data).mean() / max_value
                        
                        # If below noise gate threshold, silence the audio
                        if amplitude < self.noise_gate:
                            audio_data = np.zeros_like(audio_data)
                    
                    # Apply volume adjustment
                    if self.volume != 1.0:
                        audio_data = (audio_data * self.volume).astype(np.int16)
                    
                    # Convert back to bytes
                    data = audio_data.tobytes()
                
                # Output the processed audio
                self.output_stream.write(data)
                
        except Exception as e:
            if self.running:  # Only show error if still supposed to be running
                print(f"Error in audio processing: {e}")
                self.running = False
    
    def set_volume(self, volume):
        """Set volume multiplier (0.0-2.0)"""
        self.volume = max(0.0, min(2.0, volume))
        print(f"Volume set to {self.volume:.1f}")
        
    def increase_volume(self, amount=0.1):
        """Increase volume"""
        self.set_volume(self.volume + amount)
        
    def decrease_volume(self, amount=0.1):
        """Decrease volume"""
        self.set_volume(self.volume - amount)
        
    def set_noise_gate(self, threshold):
        """Set noise gate threshold (0.0-1.0)"""
        self.noise_gate = max(0.0, min(1.0, threshold))
        print(f"Noise gate set to {self.noise_gate:.3f}")
        
    def cleanup(self):
        """Close streams and terminate PyAudio"""
        self.running = False
        
        # Wait for processing thread to finish
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
        
        # Clean up input stream
        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except:
                pass
            self.input_stream = None
            
        # Clean up output stream
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except:
                pass
            self.output_stream = None
            
        # Terminate PyAudio instance
        if self.p:
            self.p.terminate()
            self.p = None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Audio passthrough with volume control')
    parser.add_argument('-i', '--input', help='Input device index or name')
    parser.add_argument('-o', '--output', help='Output device index or name')
    parser.add_argument('-r', '--rate', type=int, default=44100, help='Sample rate (Hz)')
    parser.add_argument('-c', '--channels', type=int, default=1, choices=[1, 2], help='Audio channels (1=mono, 2=stereo)')
    parser.add_argument('-b', '--buffer', type=int, default=1024, help='Buffer size')
    parser.add_argument('-v', '--volume', type=float, default=1.0, help='Volume multiplier')
    parser.add_argument('-n', '--noise-gate', type=float, default=0.01, help='Noise gate threshold (0-1)')
    parser.add_argument('-l', '--list', action='store_true', help='List all audio devices and exit')
    args = parser.parse_args()
    
    # Create audio passthrough object
    ap = AudioPassthrough(
        input_device=args.input,
        output_device=args.output,
        rate=args.rate,
        chunk_size=args.buffer,
        channels=args.channels,
        volume=args.volume,
        noise_gate=args.noise_gate
    )
    
    # List devices if requested
    if args.list:
        ap.list_devices()
        return
    
    # Set up signal handler for clean exit
    def signal_handler(sig, frame):
        print("\n🛑 Stopping audio passthrough...")
        ap.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start audio processing
    if ap.start():
        # Interactive volume control
        print("\nInteractive controls:")
        print("  + : Increase volume")
        print("  - : Decrease volume")
        print("  g : Increase noise gate")
        print("  f : Decrease noise gate")
        print("  q : Quit")
        
        try:
            # Enter interactive control loop
            while ap.running:
                if os.name == 'nt':  # Windows
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').lower()
                        if key == '+':
                            ap.increase_volume(0.1)
                        elif key == '-':
                            ap.decrease_volume(0.1)
                        elif key == 'g':
                            ap.set_noise_gate(ap.noise_gate + 0.01)
                        elif key == 'f':
                            ap.set_noise_gate(ap.noise_gate - 0.01)
                        elif key == 'q':
                            raise KeyboardInterrupt
                else:  # Linux/Mac
                    import select
                    import sys
                    import tty
                    import termios
                    
                    # Store old terminal settings
                    old_settings = termios.tcgetattr(sys.stdin)
                    try:
                        tty.setcbreak(sys.stdin.fileno())
                        
                        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                            key = sys.stdin.read(1).lower()
                            if key == '+':
                                ap.increase_volume(0.1)
                            elif key == '-':
                                ap.decrease_volume(0.1)
                            elif key == 'g':
                                ap.set_noise_gate(ap.noise_gate + 0.01)
                            elif key == 'f':
                                ap.set_noise_gate(ap.noise_gate - 0.01)
                            elif key == 'q':
                                raise KeyboardInterrupt
                    finally:
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user.")
        finally:
            ap.cleanup()
    
if __name__ == "__main__":
    main()