"""Main GUI application for English Whisperer"""

import sys
import os
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QGroupBox, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont

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
        
        # Initialize UI
        self._init_ui()
        
        # Initialize TTS engine after UI is ready
        QTimer.singleShot(100, self._init_tts)
    
    def _init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("English Whisperer - TTS WAV Generator")
        self.setGeometry(100, 100, 700, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel("English Whisperer")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Word list input section
        words_group = QGroupBox("Word List")
        words_layout = QVBoxLayout(words_group)
        
        instructions = QLabel("Enter words (one per line or comma-separated):")
        instructions.setFont(QFont("Arial", 9))
        words_layout.addWidget(instructions)
        
        self.word_list_text = QTextEdit()
        self.word_list_text.setFont(QFont("Arial", 10))
        self.word_list_text.setPlaceholderText("Enter words here...\nExample:\nhello\nworld\npython")
        words_layout.addWidget(self.word_list_text)
        
        main_layout.addWidget(words_group)
        
        # Output directory section
        output_group = QGroupBox("Output Directory")
        output_layout = QVBoxLayout(output_group)
        
        self.output_dir_label = QLabel("No directory selected")
        self.output_dir_label.setStyleSheet("color: gray;")
        output_layout.addWidget(self.output_dir_label)
        
        dir_layout = QHBoxLayout()
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output_dir)
        dir_layout.addWidget(browse_btn)
        
        self.output_dir_display = QLabel("")
        self.output_dir_display.setStyleSheet("color: blue;")
        self.output_dir_display.setWordWrap(True)
        dir_layout.addWidget(self.output_dir_display, 1)
        
        output_layout.addLayout(dir_layout)
        main_layout.addWidget(output_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("Generate WAV Files")
        self.generate_btn.clicked.connect(self._start_generation)
        self.generate_btn.setEnabled(False)  # Disabled until TTS is ready
        button_layout.addWidget(self.generate_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_input)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_label = QLabel("Ready")
        self.progress_label.setFont(QFont("Arial", 9))
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(progress_group)
        
        # Status log
        log_group = QGroupBox("Status Log")
        log_layout = QVBoxLayout(log_group)
        
        self.status_log = QTextEdit()
        self.status_log.setFont(QFont("Courier", 9))
        self.status_log.setReadOnly(True)
        log_layout.addWidget(self.status_log)
        
        main_layout.addWidget(log_group)
        
        # Set stretch factors
        main_layout.setStretchFactor(words_group, 2)
        main_layout.setStretchFactor(log_group, 1)
    
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
    
    def _init_tts(self):
        """Initialize the TTS generator (called after GUI is ready)"""
        try:
            # Try edge-tts first (best quality), fall back to pyttsx3
            self.tts_generator = TTSGenerator(engine="auto")
            engine_name = self.tts_generator.get_engine_name()
            is_online = self.tts_generator.is_online_required()
            self.generate_btn.setEnabled(True)
            
            status_msg = f"TTS engine initialized: {engine_name}"
            if is_online:
                status_msg += " (Requires internet connection)"
            self._log(status_msg)
            
            # Update window title to show engine
            if "Edge" in engine_name:
                self.setWindowTitle("English Whisperer - TTS WAV Generator (Neural TTS)")
            else:
                self.setWindowTitle("English Whisperer - TTS WAV Generator (System TTS)")
        except Exception as e:
            self.tts_init_error = str(e)
            self.tts_generator = None
            self.generate_btn.setEnabled(False)
            error_msg = (
                f"Failed to initialize TTS engine:\n{str(e)}\n\n"
                "Please ensure you have a TTS engine available:\n"
                "- For best quality: Install Coqui TTS (uv add TTS)\n"
                "- Fallback: Linux needs espeak/espeak-ng, Windows needs SAPI5\n\n"
                "The application will continue, but WAV generation will be disabled."
            )
            self._log(f"ERROR: {error_msg}")
            QMessageBox.critical(self, "TTS Engine Error", error_msg)
    
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
