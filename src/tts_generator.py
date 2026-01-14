"""Text-to-Speech generator with support for multiple engines"""

import os
import sys
import tempfile
from typing import Optional, Literal

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class TTSGenerator:
    """Handles text-to-speech generation and WAV file creation"""
    
    def __init__(
        self,
        engine: Literal["edge", "pyttsx3", "auto"] = "auto",
        rate: int = 150,
        volume: float = 0.9,
        voice: Optional[str] = None  # For edge-tts: voice name like "en-US-AriaNeural"
    ):
        """
        Initialize the TTS engine
        
        Args:
            engine: TTS engine to use ("edge", "pyttsx3", or "auto" for best available)
            rate: Speech rate (words per minute), default 150 (only for pyttsx3)
            volume: Volume level (0.0 to 1.0), default 0.9 (only for pyttsx3)
            voice: Voice name for edge-tts (e.g., "en-US-AriaNeural"), None for default
        """
        self.engine_type = engine
        self.rate = rate
        self.volume = volume
        self.edge_voice = voice
        self.pyttsx3_engine = None
        self.current_engine = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the TTS engine"""
        if self.engine_type == "auto":
            # Try edge-tts first (best quality), fall back to pyttsx3
            if EDGE_TTS_AVAILABLE:
                self.current_engine = "edge"
                return
            
            if PYTTSX3_AVAILABLE:
                self._init_pyttsx3()
            else:
                raise RuntimeError(
                    "No TTS engine available. Please install edge-tts or pyttsx3.\n"
                    "Install with: uv add edge-tts"
                )
        
        elif self.engine_type == "edge":
            if not EDGE_TTS_AVAILABLE:
                raise RuntimeError(
                    "edge-tts not available. Install with: uv add edge-tts"
                )
            self.current_engine = "edge"
        
        elif self.engine_type == "pyttsx3":
            if not PYTTSX3_AVAILABLE:
                raise RuntimeError(
                    "pyttsx3 not available. Install with: uv add pyttsx3"
                )
            self._init_pyttsx3()
        
        else:
            raise ValueError(f"Unknown engine type: {self.engine_type}")
    
    def _init_pyttsx3(self):
        """Initialize pyttsx3 TTS engine"""
        try:
            # Try to initialize with explicit driver on Linux for better compatibility
            if sys.platform == 'linux':
                try:
                    # Try espeak driver explicitly
                    self.pyttsx3_engine = pyttsx3.init('espeak')
                except (RuntimeError, OSError):
                    # Fall back to default initialization
                    self.pyttsx3_engine = pyttsx3.init()
            else:
                self.pyttsx3_engine = pyttsx3.init()
            
            self.pyttsx3_engine.setProperty('rate', self.rate)
            self.pyttsx3_engine.setProperty('volume', self.volume)
            self.current_engine = "pyttsx3"
        except Exception as e:
            raise RuntimeError(f"Failed to initialize pyttsx3: {str(e)}")
    
    async def _get_edge_voice(self):
        """Get the best English voice for edge-tts"""
        if self.edge_voice:
            return self.edge_voice
        
        # Get list of available voices
        voices = await edge_tts.list_voices()
        
        # Find a good English (US) neural voice
        for voice in voices:
            if voice["Locale"].startswith("en-") and "Neural" in voice["ShortName"]:
                # Prefer female voices (Aria, Jenny, etc.)
                if any(name in voice["ShortName"] for name in ["Aria", "Jenny", "Michelle"]):
                    return voice["ShortName"]
        
        # Fall back to any English neural voice
        for voice in voices:
            if voice["Locale"].startswith("en-") and "Neural" in voice["ShortName"]:
                return voice["ShortName"]
        
        # Default fallback
        return "en-US-AriaNeural"
    
    def generate_wav(self, text: str, output_path: str) -> bool:
        """
        Generate a WAV file from text
        
        Args:
            text: Text to convert to speech
            output_path: Path where the WAV file should be saved
            
        Returns:
            True if successful, False otherwise
        """
        if not self.current_engine:
            raise RuntimeError("TTS engine not initialized")
        
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            if self.current_engine == "edge":
                return self._generate_edge(text, output_path)
            else:
                return self._generate_pyttsx3(text, output_path)
        except Exception as e:
            raise RuntimeError(f"Failed to generate WAV file: {str(e)}")
    
    def _generate_edge(self, text: str, output_path: str) -> bool:
        """Generate WAV using edge-tts"""
        import asyncio
        
        async def _generate():
            # Get voice
            voice = await self._get_edge_voice()
            
            # Generate speech
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
        
        try:
            # Run async function
            asyncio.run(_generate())
            
            # Verify the file was created and has content
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise RuntimeError("edge-tts failed to generate audio")
            
            return True
        except Exception as e:
            raise RuntimeError(f"edge-tts generation failed: {str(e)}") from e
    
    def _generate_pyttsx3(self, text: str, output_path: str) -> bool:
        """Generate WAV using pyttsx3"""
        temp_path = None
        try:
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate speech to temporary file
            self.pyttsx3_engine.save_to_file(text, temp_path)
            self.pyttsx3_engine.runAndWait()
            
            # Verify the file was created and has content
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise RuntimeError("pyttsx3 failed to generate audio")
            
            # Move the temporary file to the output path
            import shutil
            shutil.move(temp_path, output_path)
            temp_path = None  # Don't delete if move succeeded
            
            return True
            
        except Exception as e:
            # Clean up temp file if it exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise
    
    def get_available_voices(self):
        """Get list of available voices"""
        if self.current_engine == "edge":
            # For edge-tts, we'd need async to list voices
            # Return a placeholder for now
            return [{"name": "Edge TTS Neural Voice", "type": "neural"}]
        elif self.current_engine == "pyttsx3":
            if not self.pyttsx3_engine:
                return []
            return self.pyttsx3_engine.getProperty('voices')
        return []
    
    def get_engine_name(self) -> str:
        """Get the name of the current engine"""
        if self.current_engine == "edge":
            return "Microsoft Edge TTS (Neural, Online)"
        elif self.current_engine == "pyttsx3":
            return "pyttsx3 (System TTS, Offline)"
        return "Unknown"
    
    def is_online_required(self) -> bool:
        """Check if the current engine requires internet connection"""
        return self.current_engine == "edge"
    
    def set_voice(self, voice_id: Optional[int] = None):
        """
        Set the voice to use (only for pyttsx3)
        
        Args:
            voice_id: Index of the voice in available voices list, or None for default
        """
        if self.current_engine != "pyttsx3":
            raise RuntimeError("Voice selection only available for pyttsx3 engine")
        
        if not self.pyttsx3_engine:
            raise RuntimeError("TTS engine not initialized")
        
        voices = self.get_available_voices()
        if voice_id is not None and 0 <= voice_id < len(voices):
            self.pyttsx3_engine.setProperty('voice', voices[voice_id].id)
        elif voice_id is not None:
            raise ValueError(f"Invalid voice index: {voice_id}")
    
    def cleanup(self):
        """Clean up the TTS engine resources"""
        if self.pyttsx3_engine:
            try:
                self.pyttsx3_engine.stop()
            except Exception:
                pass
            self.pyttsx3_engine = None
        
        self.current_engine = None
