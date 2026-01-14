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
        voice: Optional[str] = None,  # For edge-tts: voice name like "en-US-AriaNeural"
        language: Literal["en", "de"] = "en"  # Language: "en" for English, "de" for German
    ):
        """
        Initialize the TTS engine
        
        Args:
            engine: TTS engine to use ("edge", "pyttsx3", or "auto" for best available)
            rate: Speech rate (words per minute), default 150 (only for pyttsx3)
            volume: Volume level (0.0 to 1.0), default 0.9 (only for pyttsx3)
            voice: Voice name for edge-tts (e.g., "en-US-AriaNeural"), None for auto-select
            language: Language code ("en" for English, "de" for German)
        """
        self.engine_type = engine
        self.rate = rate
        self.volume = volume
        self.edge_voice = voice
        self.language = language
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
            
            # Set language for pyttsx3 (if supported)
            # Note: Language support depends on the underlying TTS engine
            # espeak supports language codes like 'de' for German
            if sys.platform == 'linux' and self.language == "de":
                try:
                    # Try to set German language for espeak
                    # This is engine-specific and may not work on all systems
                    voices = self.pyttsx3_engine.getProperty('voices')
                    for voice in voices:
                        if 'german' in voice.name.lower() or 'de' in voice.id.lower():
                            self.pyttsx3_engine.setProperty('voice', voice.id)
                            break
                except Exception:
                    # If language setting fails, continue with default voice
                    pass
            
            self.current_engine = "pyttsx3"
        except Exception as e:
            raise RuntimeError(f"Failed to initialize pyttsx3: {str(e)}")
    
    def set_language(self, language: Literal["en", "de"]):
        """
        Set the language for TTS generation
        
        Args:
            language: Language code ("en" for English, "de" for German)
        """
        if language not in ("en", "de"):
            raise ValueError(f"Unsupported language: {language}. Use 'en' or 'de'")
        
        self.language = language
        
        # For edge-tts, we'll use the new language on next generation
        # For pyttsx3, we need to reinitialize to change language
        if self.current_engine == "pyttsx3":
            try:
                self._init_pyttsx3()
            except Exception:
                # If reinitialization fails, keep the old engine
                pass
    
    async def _get_edge_voice(self):
        """Get the best voice for edge-tts based on selected language"""
        if self.edge_voice:
            return self.edge_voice
        
        # Get list of available voices
        voices = await edge_tts.list_voices()
        
        # Language-specific voice selection with preferred defaults
        if self.language == "de":
            # Default: Amala (DE)
            for voice in voices:
                if voice["ShortName"] == "de-DE-AmalaNeural":
                    return voice["ShortName"]
            
            # Fall back to any German neural voice
            for voice in voices:
                if voice["Locale"].startswith("de-") and "Neural" in voice["ShortName"]:
                    return voice["ShortName"]
            
            # Default fallback for German
            return "de-DE-AmalaNeural"
        
        else:  # English (default)
            # Default: Libby (UK)
            for voice in voices:
                if voice["ShortName"] == "en-GB-LibbyNeural":
                    return voice["ShortName"]
            
            # Fall back to any English neural voice
            for voice in voices:
                if voice["Locale"].startswith("en-") and "Neural" in voice["ShortName"]:
                    return voice["ShortName"]
            
            # Default fallback for English
            return "en-GB-LibbyNeural"
    
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
            
            # Calculate rate as percentage offset from normal (150 WPM)
            # Edge TTS rate format: '+0%' (normal), '+50%' (faster), '-25%' (slower)
            # Convert WPM to percentage: (WPM - 150) / 150 * 100
            if self.rate != 150:
                rate_percent = int((self.rate - 150) / 150.0 * 100)
                rate_str = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"
            else:
                rate_str = "+0%"  # Normal speed
            
            # Generate speech with rate parameter (no SSML needed!)
            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
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
            
        except Exception:
            # Clean up temp file if it exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise
    
    async def _list_edge_voices_async(self, language: Optional[str] = None):
        """List available edge-tts voices (async)"""
        if not EDGE_TTS_AVAILABLE:
            return []
        
        voices = await edge_tts.list_voices()
        
        if language:
            # Filter by language
            lang_prefix = language + "-"
            filtered = [v for v in voices if v["Locale"].startswith(lang_prefix)]
            return filtered
        
        return voices
    
    def get_available_voices(self):
        """Get list of available voices (synchronous wrapper)"""
        if self.current_engine == "edge":
            # For edge-tts, we need async - return cached list or empty
            # This will be populated by async method
            return []
        elif self.current_engine == "pyttsx3":
            if not self.pyttsx3_engine:
                return []
            voices = self.pyttsx3_engine.getProperty('voices')
            # Convert to list of dicts for consistency
            result = []
            for i, voice in enumerate(voices):
                result.append({
                    "id": voice.id,
                    "name": voice.name,
                    "index": i
                })
            return result
        return []
    
    async def get_available_edge_voices(self, language: Optional[str] = None):
        """Get list of available edge-tts voices for the current language"""
        if not EDGE_TTS_AVAILABLE:
            return []
        
        voices = await self._list_edge_voices_async(language or self.language)
        
        # Format for display with user-friendly names
        result = []
        for voice in voices:
            if "Neural" in voice["ShortName"]:  # Only show neural voices
                # Extract voice name (e.g., "Aria" from "en-US-AriaNeural")
                short_name = voice["ShortName"]
                voice_name = short_name.split("-")[-1].replace("Neural", "").replace("Multilingual", "")
                
                # Get gender
                gender = voice.get("Gender", "Unknown")
                gender_symbol = "♀" if gender == "Female" else "♂" if gender == "Male" else ""
                
                # Get locale info (e.g., "US" from "en-US")
                locale = voice.get("Locale", "")
                locale_parts = locale.split("-")
                country = locale_parts[1] if len(locale_parts) > 1 else ""
                
                # Create user-friendly display name
                # Format: "Aria ♀ (US)" or "Katja ♀ (DE)"
                if country:
                    display_name = f"{voice_name} {gender_symbol} ({country})"
                else:
                    display_name = f"{voice_name} {gender_symbol}"
                
                result.append({
                    "id": short_name,
                    "name": display_name,
                    "friendly_name": voice.get("FriendlyName", short_name),
                    "locale": locale,
                    "gender": gender,
                    "short_name": short_name
                })
        
        return result
    
    def set_rate(self, rate: int):
        """
        Set the speech rate (words per minute)
        
        Args:
            rate: Speech rate in words per minute (typically 50-300)
        """
        if rate < 50 or rate > 300:
            raise ValueError("Rate must be between 50 and 300 words per minute")
        
        self.rate = rate
        
        # Update pyttsx3 if it's the current engine
        if self.current_engine == "pyttsx3" and self.pyttsx3_engine:
            try:
                self.pyttsx3_engine.setProperty('rate', rate)
            except Exception:
                pass  # Ignore errors
    
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
    
    def set_voice(self, voice: Optional[str] = None):
        """
        Set the voice to use
        
        Args:
            voice: For edge-tts: voice name (e.g., "en-US-AriaNeural")
                   For pyttsx3: voice index (int) or None for default
        """
        if self.current_engine == "edge":
            # For edge-tts, set the voice name directly
            self.edge_voice = voice
        elif self.current_engine == "pyttsx3":
            if not self.pyttsx3_engine:
                raise RuntimeError("TTS engine not initialized")
            
            if voice is not None:
                try:
                    # Try as index first
                    voice_id = int(voice)
                    voices = self.get_available_voices()
                    if 0 <= voice_id < len(voices):
                        self.pyttsx3_engine.setProperty('voice', voices[voice_id]["id"])
                    else:
                        raise ValueError(f"Invalid voice index: {voice_id}")
                except (ValueError, TypeError):
                    # Try as voice ID string
                    self.pyttsx3_engine.setProperty('voice', voice)
        else:
            raise RuntimeError("TTS engine not initialized")
    
    def cleanup(self):
        """Clean up the TTS engine resources"""
        if self.pyttsx3_engine:
            try:
                self.pyttsx3_engine.stop()
            except Exception:
                pass
            self.pyttsx3_engine = None
        
        self.current_engine = None
