"""
Audio Player module
Handles playing audio files using PyAudio
"""

import os
import time
import threading
import wave
import tempfile
import subprocess
from typing import Callable, Optional
import pyaudio

class AudioPlayer:
    """
    Audio player for playing audio files with basic controls
    """
    
    def __init__(self):
        """Initialize audio player"""
        self.pyaudio = pyaudio.PyAudio()
        self.stream = None
        self.playing = False
        self.paused = False
        self.stop_event = threading.Event()
        self.current_file = None
        self.current_info = None
        self.playback_thread = None
        self.position = 0
        self.duration = 0
        self.on_progress_callback = None
        self.on_complete_callback = None
    
    def play(self, file_path: str, video_info: dict, 
             on_progress: Optional[Callable] = None, 
             on_complete: Optional[Callable] = None) -> bool:
        """
        Play an audio file
        
        Args:
            file_path: Path to the audio file
            video_info: Dictionary containing video information
            on_progress: Callback function for playback progress updates
            on_complete: Callback function called when playback completes
            
        Returns:
            True if playback started successfully, False otherwise
        """
        # Stop any currently playing audio
        self.stop()
        
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return False
            
            # Store file information
            self.current_file = file_path
            self.current_info = video_info
            self.on_progress_callback = on_progress
            self.on_complete_callback = on_complete
            
            # Reset playback state
            self.playing = True
            self.paused = False
            self.stop_event.clear()
            self.position = 0
            
            # Start playback in a separate thread
            self.playback_thread = threading.Thread(
                target=self._play_audio,
                args=(file_path,)
            )
            self.playback_thread.daemon = True
            self.playback_thread.start()
            
            return True
        
        except Exception as e:
            print(f"Error playing audio: {str(e)}")
            self.playing = False
            self.current_file = None
            self.current_info = None
            return False
    
    def _play_audio(self, file_path: str):
        """
        Internal method to play audio in a separate thread
        
        Args:
            file_path: Path to the audio file
        """
        try:
            # Handle different audio formats
            if file_path.endswith('.mp4'):
                # Convert MP4 to WAV for playback
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                    temp_wav_path = temp_wav.name
                
                # Use ffmpeg to convert MP4 to WAV
                conversion_cmd = [
                    'ffmpeg', 
                    '-i', file_path, 
                    '-vn',  # No video
                    '-acodec', 'pcm_s16le',  # PCM format
                    '-ar', '44100',  # Sample rate
                    '-ac', '2',  # Stereo
                    temp_wav_path
                ]
                
                subprocess.run(conversion_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Open the converted WAV file
                file_to_play = temp_wav_path
            else:
                # Use the original file if it's already in a supported format
                file_to_play = file_path
            
            # Open the audio file
            with wave.open(file_to_play, 'rb') as wf:
                # Get audio file properties
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                framerate = wf.getframerate()
                self.duration = wf.getnframes() / framerate
                
                # Create a PyAudio stream
                self.stream = self.pyaudio.open(
                    format=self.pyaudio.get_format_from_width(sample_width),
                    channels=channels,
                    rate=framerate,
                    output=True,
                    stream_callback=self._stream_callback
                )
                
                # Store the audio file data for callback
                self.audio_data = wf.readframes(wf.getnframes())
                self.audio_pos = 0
                self.channels = channels
                self.sample_width = sample_width
                self.framerate = framerate
                
                # Start the stream
                self.stream.start_stream()
                
                # Wait until playback is complete or stopped
                start_time = time.time()
                while self.stream.is_active() and not self.stop_event.is_set():
                    if not self.paused:
                        self.position = time.time() - start_time
                        
                        # Call progress callback if provided
                        if self.on_progress_callback:
                            self.on_progress_callback(self.position, self.duration)
                    
                    time.sleep(0.1)
                
                # Clean up
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
                
                # Remove temporary WAV file if it was created
                if file_path.endswith('.mp4') and os.path.exists(temp_wav_path):
                    os.unlink(temp_wav_path)
                
                # Call complete callback if provided and playback completed naturally
                if not self.stop_event.is_set() and self.on_complete_callback:
                    self.on_complete_callback()
                
                self.playing = False
        
        except Exception as e:
            print(f"Playback error: {str(e)}")
            self.playing = False
            if self.stream:
                self.stream.close()
                self.stream = None
    
    def _stream_callback(self, in_data, frame_count, time_info, status):
        """
        Callback function for the PyAudio stream
        
        Args:
            in_data: Input audio data (not used)
            frame_count: Number of frames to process
            time_info: Dictionary with timing information
            status: Status flag
            
        Returns:
            Tuple containing (data, flag)
        """
        if self.paused:
            # Return empty data while paused
            return b'\x00' * frame_count * self.channels * self.sample_width, pyaudio.paContinue
        
        # Calculate how many bytes to read
        bytes_per_frame = self.channels * self.sample_width
        bytes_to_read = frame_count * bytes_per_frame
        
        # Read data from the audio buffer
        if self.audio_pos + bytes_to_read > len(self.audio_data):
            # End of file
            data = self.audio_data[self.audio_pos:]
            self.audio_pos = len(self.audio_data)
            return data, pyaudio.paComplete
        else:
            # Middle of file
            data = self.audio_data[self.audio_pos:self.audio_pos + bytes_to_read]
            self.audio_pos += bytes_to_read
            return data, pyaudio.paContinue
    
    def pause(self):
        """Pause playback"""
        if self.playing and not self.paused:
            self.paused = True
    
    def resume(self):
        """Resume playback"""
        if self.playing and self.paused:
            self.paused = False
    
    def toggle_pause(self):
        """Toggle pause state"""
        if self.playing:
            if self.paused:
                self.resume()
            else:
                self.pause()
    
    def stop(self):
        """Stop playback"""
        if self.playing:
            self.stop_event.set()
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=1.0)
            
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            self.playing = False
            self.paused = False
    
    def is_playing(self) -> bool:
        """
        Check if audio is currently playing
        
        Returns:
            True if audio is playing, False otherwise
        """
        return self.playing and not self.paused
    
    def is_paused(self) -> bool:
        """
        Check if playback is paused
        
        Returns:
            True if playback is paused, False otherwise
        """
        return self.playing and self.paused
    
    def get_position(self) -> float:
        """
        Get current playback position in seconds
        
        Returns:
            Current playback position in seconds
        """
        return self.position
    
    def get_duration(self) -> float:
        """
        Get total duration of current track in seconds
        
        Returns:
            Total duration in seconds
        """
        return self.duration
    
    def get_current_info(self) -> dict:
        """
        Get information about the currently playing track
        
        Returns:
            Dictionary containing track information
        """
        return self.current_info
    
    def __del__(self):
        """Clean up resources when object is destroyed"""
        self.stop()
        self.pyaudio.terminate()
