"""Text-to-Speech generator using pyttsx3"""

import os
import sys
import tempfile
from typing import Optional

import pyttsx3


class TTSGenerator:
    """Handles text-to-speech generation and WAV file creation"""
    
    def __init__(self, rate: int = 150, volume: float = 0.9):
        """
        Initialize the TTS engine
        
        Args:
            rate: Speech rate (words per minute), default 150
            volume: Volume level (0.0 to 1.0), default 0.9
        """
        self.engine = None
        self.rate = rate
        self.volume = volume
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the pyttsx3 TTS engine"""
        try:
            # Try to initialize with explicit driver on Linux for better compatibility
            if sys.platform == 'linux':
                try:
                    # Try espeak driver explicitly
                    self.engine = pyttsx3.init('espeak')
                except (RuntimeError, OSError):
                    # Fall back to default initialization
                    self.engine = pyttsx3.init()
            else:
                self.engine = pyttsx3.init()
            
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize TTS engine: {str(e)}")
    
    def generate_wav(self, text: str, output_path: str) -> bool:
        """
        Generate a WAV file from text
        
        Args:
            text: Text to convert to speech
            output_path: Path where the WAV file should be saved
            
        Returns:
            True if successful, False otherwise
        """
        if not self.engine:
            raise RuntimeError("TTS engine not initialized")
        
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        try:
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate speech to temporary file
            self.engine.save_to_file(text, temp_path)
            self.engine.runAndWait()
            
            # Verify the file was created and has content
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise RuntimeError("TTS engine failed to generate audio")
            
            # Move the temporary file to the output path
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # Copy temp file to output path
            import shutil
            shutil.move(temp_path, output_path)
            
            return True
            
        except Exception as e:
            # Clean up temp file if it exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise RuntimeError(f"Failed to generate WAV file: {str(e)}")
    
    def get_available_voices(self):
        """Get list of available voices"""
        if not self.engine:
            return []
        return self.engine.getProperty('voices')
    
    def set_voice(self, voice_id: Optional[int] = None):
        """
        Set the voice to use
        
        Args:
            voice_id: Index of the voice in available voices list, or None for default
        """
        if not self.engine:
            raise RuntimeError("TTS engine not initialized")
        
        voices = self.get_available_voices()
        if voice_id is not None and 0 <= voice_id < len(voices):
            self.engine.setProperty('voice', voices[voice_id].id)
        elif voice_id is not None:
            raise ValueError(f"Invalid voice index: {voice_id}")
    
    def cleanup(self):
        """Clean up the TTS engine resources"""
        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
            self.engine = None
