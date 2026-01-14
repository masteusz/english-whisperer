"""Main GUI application for English Whisperer"""

import sys
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QGroupBox, QComboBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from .tts_generator import TTSGenerator
from .file_handler import parse_word_list, get_output_path, validate_output_directory


class GenerationWorker(QThread):
    """Worker thread for generating WAV files"""
    
    progress_update = Signal(str, int, int)  # word, current, total
    file_complete = Signal(str)  # filename
    error_occurred = Signal(str, str)  # word, error message
    finished_signal = Signal(int, int, int)  # success_count, error_count, total_count
    
    def __init__(self, words, output_dir, tts_generator, parent=None):
        super().__init__(parent)
        self.words = words
        self.output_dir = output_dir
        self.tts_generator = tts_generator
        self._is_cancelled = False
    
    def cancel(self):
        """Cancel the generation process"""
        self._is_cancelled = True
    
    def run(self):
        """Run the generation process"""
        success_count = 0
        error_count = 0
        
        try:
            for i, word in enumerate(self.words, 1):
                if self._is_cancelled:
                    break
                
                # Emit progress update
                self.progress_update.emit(word, i, len(self.words))
                
                try:
                    # Get output path
                    output_path = get_output_path(self.output_dir, word)
                    
                    # Generate WAV file
                    self.tts_generator.generate_wav(word, output_path)
                    
                    success_count += 1
                    self.file_complete.emit(os.path.basename(output_path))
                    
                except Exception as e:
                    error_count += 1
                    error_msg = str(e)
                    self.error_occurred.emit(word, error_msg)
        
        except Exception as e:
            error_msg = f"Fatal error during generation: {str(e)}"
            self.error_occurred.emit("", error_msg)
        
        finally:
            # Emit completion signal
            self.finished_signal.emit(success_count, error_count, len(self.words))


class EnglishWhispererApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Application state
        self.output_dir = ""
        self.tts_generator = None
        self.is_processing = False
        self.tts_init_error = None
        self.generation_worker = None
        self.current_language = "en"  # Default to English
        
        # Initialize UI
        self._init_ui()
        
        # Initialize TTS engine after UI is ready
        QTimer.singleShot(100, self._init_tts)
    
    def _init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("English Whisperer - TTS WAV Generator")
        self.setGeometry(100, 100, 750, 700)
        
        # Apply modern styling
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel {
                color: #333333;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QComboBox:hover {
                border: 1px solid #999999;
            }
            QRadioButton {
                spacing: 5px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Title with subtitle
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("English Whisperer")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 5px;")
        title_layout.addWidget(title_label)
        
        subtitle = QLabel("Generate WAV audio files from words")
        subtitle.setFont(QFont("Arial", 9))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d;")
        title_layout.addWidget(subtitle)
        
        main_layout.addWidget(title_container)
        
        # Settings section - moved to top for better workflow
        settings_group = QGroupBox("Voice Settings")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(10)
        
        # Language selection with tooltip
        language_layout = QHBoxLayout()
        language_label = QLabel("Language:")
        language_label.setFont(QFont("Arial", 10))
        language_label.setToolTip("Select the language for text-to-speech generation")
        language_layout.addWidget(language_label)
        
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("German (Deutsch)", "de")
        self.language_combo.setCurrentIndex(0)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        self.language_combo.setToolTip("Choose the language for speech synthesis")
        language_layout.addWidget(self.language_combo, 1)
        settings_layout.addLayout(language_layout)
        
        # Voice selection with tooltip
        voice_layout = QHBoxLayout()
        voice_label = QLabel("Voice:")
        voice_label.setFont(QFont("Arial", 10))
        voice_label.setToolTip("Select a specific voice (defaults are Libby for English, Amala for German)")
        voice_layout.addWidget(voice_label)
        
        self.voice_combo = QComboBox()
        self.voice_combo.setEnabled(False)
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        self.voice_combo.setToolTip("Choose a voice. The default voice is automatically selected based on language.")
        voice_layout.addWidget(self.voice_combo, 1)
        settings_layout.addLayout(voice_layout)
        
        # Speed selection with tooltip
        speed_layout = QHBoxLayout()
        speed_label = QLabel("Speed:")
        speed_label.setFont(QFont("Arial", 10))
        speed_label.setToolTip("Adjust the speech rate: Slower (50 WPM), Normal (100 WPM), or Faster (150 WPM)")
        speed_layout.addWidget(speed_label)
        
        self.speed_group = QButtonGroup()
        
        self.speed_slower = QRadioButton("Slower (50 WPM)")
        self.speed_slower.setEnabled(False)
        self.speed_slower.setToolTip("Slower speech rate - 50 words per minute")
        self.speed_group.addButton(self.speed_slower, 0)
        speed_layout.addWidget(self.speed_slower)
        
        self.speed_normal = QRadioButton("Normal (100 WPM)")
        self.speed_normal.setChecked(True)
        self.speed_normal.setEnabled(False)
        self.speed_normal.setToolTip("Normal speech rate - 100 words per minute (default)")
        self.speed_group.addButton(self.speed_normal, 1)
        speed_layout.addWidget(self.speed_normal)
        
        self.speed_faster = QRadioButton("Faster (150 WPM)")
        self.speed_faster.setEnabled(False)
        self.speed_faster.setToolTip("Faster speech rate - 150 words per minute")
        self.speed_group.addButton(self.speed_faster, 2)
        speed_layout.addWidget(self.speed_faster)
        
        self.speed_group.buttonClicked.connect(self._on_speed_changed)
        speed_layout.addStretch()
        settings_layout.addLayout(speed_layout)
        
        main_layout.addWidget(settings_group)
        
        # Word list input section - main focus
        words_group = QGroupBox("Word List")
        words_layout = QVBoxLayout(words_group)
        words_layout.setSpacing(8)
        
        instructions = QLabel("Enter words (one per line or comma-separated):")
        instructions.setFont(QFont("Arial", 9))
        instructions.setStyleSheet("color: #555555;")
        words_layout.addWidget(instructions)
        
        self.word_list_text = QTextEdit()
        self.word_list_text.setFont(QFont("Arial", 11))
        self.word_list_text.setPlaceholderText(
            "Enter words here, one per line or separated by commas...\n\n"
            "Examples:\n"
            "  hello\n"
            "  world\n"
            "  python\n\n"
            "Or: hello, world, python, programming"
        )
        self.word_list_text.setToolTip("Enter the words you want to convert to speech. You can use newlines or commas to separate words.")
        words_layout.addWidget(self.word_list_text)
        
        main_layout.addWidget(words_group)
        
        # Output directory section
        output_group = QGroupBox("Output Directory")
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(8)
        
        self.output_dir_label = QLabel("No directory selected")
        self.output_dir_label.setStyleSheet("color: #999999; font-style: italic;")
        self.output_dir_label.setToolTip("Select a folder where the generated WAV files will be saved")
        output_layout.addWidget(self.output_dir_label)
        
        dir_layout = QHBoxLayout()
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output_dir)
        browse_btn.setToolTip("Click to select the output folder for WAV files")
        browse_btn.setMinimumWidth(120)
        dir_layout.addWidget(browse_btn)
        
        self.output_dir_display = QLabel("")
        self.output_dir_display.setStyleSheet("color: #2980b9; padding: 5px; background-color: #ecf0f1; border-radius: 3px;")
        self.output_dir_display.setWordWrap(True)
        self.output_dir_display.setToolTip("Currently selected output directory")
        dir_layout.addWidget(self.output_dir_display, 1)
        
        output_layout.addLayout(dir_layout)
        main_layout.addWidget(output_group)
        
        # Control buttons - Generate button is prominent
        button_layout = QVBoxLayout()
        button_layout.setSpacing(12)
        
        # Main generate button - large and prominent
        self.generate_btn = QPushButton("Generate WAV Files")
        self.generate_btn.clicked.connect(self._start_generation)
        self.generate_btn.setEnabled(False)
        generate_font = QFont()
        generate_font.setPointSize(13)
        generate_font.setBold(True)
        self.generate_btn.setFont(generate_font)
        self.generate_btn.setMinimumHeight(55)
        self.generate_btn.setToolTip("Generate WAV files from the word list (Ctrl+G or Enter)")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        button_layout.addWidget(self.generate_btn)
        
        # Secondary buttons
        secondary_layout = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_input)
        clear_btn.setToolTip("Clear the word list (Ctrl+L)")
        clear_btn.setMinimumWidth(100)
        secondary_layout.addWidget(clear_btn)
        secondary_layout.addStretch()
        button_layout.addLayout(secondary_layout)
        
        main_layout.addLayout(button_layout)
        
        # Progress section with better styling
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(8)
        
        self.progress_label = QLabel("Ready - Enter words and click Generate")
        self.progress_label.setFont(QFont("Arial", 10))
        self.progress_label.setStyleSheet("color: #27ae60; font-weight: bold; padding: 5px;")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(progress_group)
        
        # Status log with better styling
        log_group = QGroupBox("Status Log")
        log_layout = QVBoxLayout(log_group)
        
        self.status_log = QTextEdit()
        self.status_log.setFont(QFont("Consolas", 9))
        self.status_log.setReadOnly(True)
        self.status_log.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        self.status_log.setToolTip("Shows status messages and generation progress")
        log_layout.addWidget(self.status_log)
        
        main_layout.addWidget(log_group)
        
        # Set stretch factors for better layout
        main_layout.setStretchFactor(words_group, 3)
        main_layout.setStretchFactor(log_group, 1)
        
        # Add keyboard shortcuts
        self._setup_shortcuts()
    
    def _setup_shortcuts(self):
        """Set up keyboard shortcuts for common actions"""
        # Generate shortcut (Ctrl+G or Enter)
        generate_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        generate_shortcut.activated.connect(self._start_generation)
        
        # Also allow Enter key when word list has focus (but not when editing)
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self.word_list_text)
        enter_shortcut.setContext(Qt.WidgetShortcut)
        enter_shortcut.activated.connect(self._start_generation)
        
        # Clear shortcut (Ctrl+L)
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self._clear_input)
        
        # Focus word list (Ctrl+W)
        focus_words_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        focus_words_shortcut.activated.connect(lambda: self.word_list_text.setFocus())
    
    def _browse_output_dir(self):
        """Open directory browser"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.output_dir or os.path.expanduser("~")
        )
        if directory:
            self.output_dir = directory
            self.output_dir_label.setText("Selected:")
            self.output_dir_label.setStyleSheet("color: black;")
            # Truncate long paths for display
            display_path = directory
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            self.output_dir_display.setText(display_path)
            self._log(f"Output directory set to: {directory}")
    
    def _clear_input(self):
        """Clear the word list input"""
        self.word_list_text.clear()
        self._log("Input cleared")
    
    def _log(self, message: str):
        """Add a message to the status log"""
        self.status_log.append(message)
        # Auto-scroll to bottom
        scrollbar = self.status_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _get_speed_value(self) -> int:
        """Get the current speed value from radio buttons"""
        if self.speed_slower.isChecked():
            return 50  # Slower
        elif self.speed_faster.isChecked():
            return 150  # Faster
        else:
            return 100  # Normal (default)
    
    def _init_tts(self):
        """Initialize the TTS generator (called after GUI is ready)"""
        try:
            # Get current language and speed from UI
            language = self.language_combo.currentData()
            speed = self._get_speed_value()
            
            # Try edge-tts first (best quality), fall back to pyttsx3
            self.tts_generator = TTSGenerator(engine="auto", language=language, rate=speed)
            self.current_language = language
            engine_name = self.tts_generator.get_engine_name()
            is_online = self.tts_generator.is_online_required()
            self.generate_btn.setEnabled(True)
            # Enable speed radio buttons
            self.speed_slower.setEnabled(True)
            self.speed_normal.setEnabled(True)
            self.speed_faster.setEnabled(True)
            
            lang_name = "English" if language == "en" else "German"
            status_msg = f"TTS engine initialized: {engine_name} ({lang_name})"
            if is_online:
                status_msg += " (Requires internet connection)"
            self._log(status_msg)
            
            # Load voices for the current language
            self._load_voices()
            
            # Update window title to show engine
            if "Edge" in engine_name:
                self.setWindowTitle("English Whisperer - TTS WAV Generator (Neural TTS)")
            else:
                self.setWindowTitle("English Whisperer - TTS WAV Generator (System TTS)")
        except Exception as e:
            self.tts_init_error = str(e)
            self.tts_generator = None
            self.generate_btn.setEnabled(False)
            # Disable speed radio buttons
            self.speed_slower.setEnabled(False)
            self.speed_normal.setEnabled(False)
            self.speed_faster.setEnabled(False)
            error_msg = (
                f"Failed to initialize TTS engine:\n{str(e)}\n\n"
                "Please ensure you have a TTS engine available:\n"
                "- For best quality: Install edge-tts (uv add edge-tts)\n"
                "- Fallback: Linux needs espeak/espeak-ng, Windows needs SAPI5\n\n"
                "The application will continue, but WAV generation will be disabled."
            )
            self._log(f"ERROR: {error_msg}")
            QMessageBox.critical(self, "TTS Engine Error", error_msg)
    
    def _load_voices(self):
        """Load available voices for the current language"""
        if not self.tts_generator:
            return
        
        self.voice_combo.clear()
        self.voice_combo.blockSignals(True)
        
        try:
            if self.tts_generator.current_engine == "edge":
                # Load edge-tts voices asynchronously
                import asyncio
                try:
                    voices = asyncio.run(self.tts_generator.get_available_edge_voices(self.current_language))
                    if voices:
                        default_voice_id = "en-GB-LibbyNeural" if self.current_language == "en" else "de-DE-AmalaNeural"
                        default_index = 0
                        
                        for i, voice in enumerate(voices):
                            # Use the user-friendly name we created
                            display_name = voice["name"]
                            self.voice_combo.addItem(display_name, voice["id"])
                            # Check if this is the default voice
                            if voice["id"] == default_voice_id:
                                default_index = i
                        
                        # Set the default voice as selected (signals are already blocked)
                        self.voice_combo.setCurrentIndex(default_index)
                        # Set the voice in the TTS generator
                        if self.tts_generator:
                            try:
                                self.tts_generator.set_voice(default_voice_id)
                            except Exception:
                                pass  # Voice might not be available yet
                        
                        self.voice_combo.setEnabled(True)
                        default_voice_name = voices[default_index]['name'] if default_index < len(voices) else 'Auto'
                        self._log(f"Loaded {len(voices)} voices for {self.current_language} (default: {default_voice_name})")
                    else:
                        self.voice_combo.addItem("Auto (Default)", None)
                        self.voice_combo.setEnabled(False)
                except Exception as e:
                    self._log(f"Warning: Could not load voices: {str(e)}")
                    self.voice_combo.addItem("Auto (Default)", None)
                    self.voice_combo.setEnabled(False)
            else:
                # Load pyttsx3 voices
                voices = self.tts_generator.get_available_voices()
                if voices:
                    for voice in voices:
                        self.voice_combo.addItem(voice["name"], voice["id"])
                    self.voice_combo.setEnabled(True)
                    self._log(f"Loaded {len(voices)} system voices")
                else:
                    self.voice_combo.addItem("Default", None)
                    self.voice_combo.setEnabled(False)
        except Exception as e:
            self._log(f"Warning: Could not load voices: {str(e)}")
            self.voice_combo.addItem("Auto (Default)", None)
            self.voice_combo.setEnabled(False)
        finally:
            self.voice_combo.blockSignals(False)
    
    def _on_language_changed(self, index: int):
        """Handle language selection change"""
        if self.is_processing:
            QMessageBox.warning(
                self,
                "Cannot Change Language",
                "Please wait for the current generation to complete before changing the language."
            )
            # Reset to previous language
            self.language_combo.blockSignals(True)
            prev_lang = "en" if self.current_language == "de" else "de"
            prev_index = 0 if prev_lang == "en" else 1
            self.language_combo.setCurrentIndex(prev_index)
            self.language_combo.blockSignals(False)
            return
        
        new_language = self.language_combo.currentData()
        
        if new_language == self.current_language:
            return
        
        self.current_language = new_language
        lang_name = "English" if new_language == "en" else "German"
        self._log(f"Language changed to: {lang_name}")
        
        # Update TTS generator language if it exists
        if self.tts_generator:
            try:
                self.tts_generator.set_language(new_language)
                self._log(f"TTS engine updated for {lang_name}")
                # Reload voices for the new language
                self._load_voices()
            except Exception as e:
                self._log(f"Warning: Could not update TTS language: {str(e)}")
                QMessageBox.warning(
                    self,
                    "Language Update Warning",
                    f"Could not update TTS engine language: {str(e)}\n\n"
                    "The language change will take effect on the next generation."
                )
    
    def _on_voice_changed(self, index: int):
        """Handle voice selection change"""
        if not self.tts_generator or self.is_processing:
            return
        
        voice_id = self.voice_combo.currentData()
        if voice_id is None:
            # Auto/default voice
            if self.tts_generator.current_engine == "edge":
                self.tts_generator.edge_voice = None
            self._log("Voice set to: Auto (Default)")
        else:
            try:
                self.tts_generator.set_voice(voice_id)
                voice_name = self.voice_combo.currentText()
                self._log(f"Voice changed to: {voice_name}")
            except Exception as e:
                self._log(f"Warning: Could not set voice: {str(e)}")
    
    def _on_speed_changed(self, button):
        """Handle speed/rate change from radio buttons"""
        if not self.tts_generator or self.is_processing:
            return
        
        try:
            speed = self._get_speed_value()
            speed_name = "Slower" if speed == 50 else "Faster" if speed == 150 else "Normal"
            self.tts_generator.set_rate(speed)
            self._log(f"Speed set to: {speed_name} ({speed} WPM)")
        except Exception as e:
            self._log(f"Warning: Could not set speed: {str(e)}")
    
    def _start_generation(self):
        """Start the WAV generation process"""
        if self.is_processing:
            QMessageBox.warning(self, "Already Processing", "Generation is already in progress.")
            return
        
        if not self.tts_generator:
            if self.tts_init_error:
                QMessageBox.critical(
                    self,
                    "TTS Engine Error",
                    f"TTS engine is not available.\n\n{self.tts_init_error}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "TTS Engine Not Ready",
                    "TTS engine is still initializing. Please wait a moment and try again."
                )
            return
        
        # Get word list
        word_list_text = self.word_list_text.toPlainText().strip()
        if not word_list_text:
            QMessageBox.warning(self, "No Words", "Please enter at least one word.")
            return
        
        # Validate output directory
        if not self.output_dir:
            QMessageBox.warning(self, "No Output Directory", "Please select an output directory.")
            return
        
        is_valid, error_msg = validate_output_directory(self.output_dir)
        if not is_valid:
            QMessageBox.critical(self, "Invalid Directory", error_msg)
            return
        
        # Parse word list
        words = parse_word_list(word_list_text)
        if not words:
            QMessageBox.warning(self, "No Valid Words", "Could not parse any valid words from input.")
            return
        
        # Start generation
        self.is_processing = True
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setText(f"Processing {len(words)} words...")
        self.progress_label.setStyleSheet("color: #3498db; font-weight: bold; padding: 5px;")
        self._log(f"\n=== Starting generation of {len(words)} words ===")
        
        # Create and start worker thread
        self.generation_worker = GenerationWorker(words, self.output_dir, self.tts_generator)
        self.generation_worker.progress_update.connect(self._on_progress_update)
        self.generation_worker.file_complete.connect(self._on_file_complete)
        self.generation_worker.error_occurred.connect(self._on_error_occurred)
        self.generation_worker.finished_signal.connect(self._on_generation_complete)
        self.generation_worker.start()
    
    def _on_progress_update(self, word: str, current: int, total: int):
        """Handle progress update from worker thread"""
        self.progress_label.setText(f"Processing: {word} ({current}/{total})")
        self.progress_label.setStyleSheet("color: #3498db; font-weight: bold; padding: 5px;")
        self._log(f"[{current}/{total}] Processing: {word}")
    
    def _on_file_complete(self, filename: str):
        """Handle file completion from worker thread"""
        self._log(f"  ✓ Saved: {filename}")
    
    def _on_error_occurred(self, word: str, error_msg: str):
        """Handle error from worker thread"""
        if word:
            self._log(f"  ✗ Error for '{word}': {error_msg}")
        else:
            self._log(f"  ✗ {error_msg}")
            QMessageBox.critical(self, "Generation Error", error_msg)
    
    def _on_generation_complete(self, success_count: int, error_count: int, total_count: int):
        """Handle generation completion"""
        self.is_processing = False
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        # Show completion message
        if success_count == total_count:
            self.progress_label.setText(f"Complete! Generated {success_count} WAV files.")
            self.progress_label.setStyleSheet("color: #27ae60; font-weight: bold; padding: 5px;")
            self._log(f"\n=== Generation complete: {success_count} files created ===")
            QMessageBox.information(
                self,
                "Generation Complete",
                f"Successfully generated {success_count} WAV files!\n\n"
                f"Output directory: {self.output_dir}"
            )
        else:
            self.progress_label.setText(
                f"Complete: {success_count} succeeded, {error_count} failed"
            )
            self.progress_label.setStyleSheet("color: #f39c12; font-weight: bold; padding: 5px;")
            self._log(
                f"\n=== Generation complete: {success_count} succeeded, {error_count} failed ==="
            )
            QMessageBox.warning(
                self,
                "Generation Complete with Errors",
                f"Generated {success_count} out of {total_count} WAV files.\n\n"
                f"{error_count} errors occurred. Check the status log for details."
            )
        
        # Clean up worker
        if self.generation_worker:
            self.generation_worker.wait()
            self.generation_worker = None
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.is_processing:
            reply = QMessageBox.question(
                self,
                "Quit",
                "Generation in progress. Cancel and quit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.generation_worker:
                    self.generation_worker.cancel()
                    self.generation_worker.wait()
                if self.tts_generator:
                    self.tts_generator.cleanup()
                event.accept()
            else:
                event.ignore()
        else:
            if self.tts_generator:
                self.tts_generator.cleanup()
            event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("English Whisperer")
    
    window = EnglishWhispererApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
