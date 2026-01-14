"""Main GUI application for English Whisperer"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
from pathlib import Path

from .tts_generator import TTSGenerator
from .file_handler import parse_word_list, get_output_path, validate_output_directory


class EnglishWhispererApp:
    """Main application window"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("English Whisperer - TTS WAV Generator")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        # Application state
        self.output_dir = ""
        self.tts_generator = None
        self.is_processing = False
        
        # Initialize TTS engine
        self._init_tts()
        
        # Build UI
        self._build_ui()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _init_tts(self):
        """Initialize the TTS generator"""
        try:
            self.tts_generator = TTSGenerator()
        except Exception as e:
            messagebox.showerror(
                "TTS Engine Error",
                f"Failed to initialize TTS engine:\n{str(e)}\n\n"
                "Please ensure you have the required TTS system installed:\n"
                "- Linux: espeak or espeak-ng\n"
                "- Windows: SAPI5 (usually pre-installed)"
            )
            self.tts_generator = None
    
    def _build_ui(self):
        """Build the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="English Whisperer",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        # Word list input section
        words_frame = ttk.LabelFrame(main_frame, text="Word List", padding="5")
        words_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        words_frame.columnconfigure(0, weight=1)
        words_frame.rowconfigure(0, weight=1)
        
        # Instructions
        instructions = ttk.Label(
            words_frame,
            text="Enter words (one per line or comma-separated):",
            font=("Arial", 9)
        )
        instructions.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Text area for word list
        self.word_list_text = scrolledtext.ScrolledText(
            words_frame,
            height=10,
            wrap=tk.WORD,
            font=("Arial", 10)
        )
        self.word_list_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Output directory section
        output_frame = ttk.LabelFrame(main_frame, text="Output Directory", padding="5")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        
        # Output directory label
        self.output_dir_label = ttk.Label(
            output_frame,
            text="No directory selected",
            foreground="gray"
        )
        self.output_dir_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # Browse button
        browse_btn = ttk.Button(
            output_frame,
            text="Browse...",
            command=self._browse_output_dir
        )
        browse_btn.grid(row=1, column=0, padx=(0, 5))
        
        # Selected directory display
        self.output_dir_display = ttk.Label(
            output_frame,
            text="",
            foreground="blue"
        )
        self.output_dir_display.grid(row=1, column=1, sticky=tk.W)
        
        # Control buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=(0, 10))
        
        # Generate button
        self.generate_btn = ttk.Button(
            button_frame,
            text="Generate WAV Files",
            command=self._start_generation,
            state=tk.NORMAL if self.tts_generator else tk.DISABLED
        )
        self.generate_btn.grid(row=0, column=0, padx=5)
        
        # Clear button
        clear_btn = ttk.Button(
            button_frame,
            text="Clear",
            command=self._clear_input
        )
        clear_btn.grid(row=0, column=1, padx=5)
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="5")
        progress_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_label = ttk.Label(
            progress_frame,
            textvariable=self.progress_var,
            font=("Arial", 9)
        )
        self.progress_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Progress bar widget
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='indeterminate'
        )
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Status log
        log_frame = ttk.LabelFrame(main_frame, text="Status Log", padding="5")
        log_frame.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        # Status log text area
        self.status_log = scrolledtext.ScrolledText(
            log_frame,
            height=6,
            wrap=tk.WORD,
            font=("Courier", 9),
            state=tk.DISABLED
        )
        self.status_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def _browse_output_dir(self):
        """Open directory browser"""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir = directory
            self.output_dir_label.config(text="Selected:", foreground="black")
            # Truncate long paths for display
            display_path = directory
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            self.output_dir_display.config(text=display_path)
            self._log(f"Output directory set to: {directory}")
    
    def _clear_input(self):
        """Clear the word list input"""
        self.word_list_text.delete(1.0, tk.END)
        self._log("Input cleared")
    
    def _log(self, message: str):
        """Add a message to the status log"""
        self.status_log.config(state=tk.NORMAL)
        self.status_log.insert(tk.END, message + "\n")
        self.status_log.see(tk.END)
        self.status_log.config(state=tk.DISABLED)
    
    def _start_generation(self):
        """Start the WAV generation process in a separate thread"""
        if self.is_processing:
            messagebox.showwarning("Already Processing", "Generation is already in progress.")
            return
        
        if not self.tts_generator:
            messagebox.showerror("TTS Engine Error", "TTS engine is not available.")
            return
        
        # Get word list
        word_list_text = self.word_list_text.get(1.0, tk.END).strip()
        if not word_list_text:
            messagebox.showwarning("No Words", "Please enter at least one word.")
            return
        
        # Validate output directory
        if not self.output_dir:
            messagebox.showwarning("No Output Directory", "Please select an output directory.")
            return
        
        is_valid, error_msg = validate_output_directory(self.output_dir)
        if not is_valid:
            messagebox.showerror("Invalid Directory", error_msg)
            return
        
        # Parse word list
        words = parse_word_list(word_list_text)
        if not words:
            messagebox.showwarning("No Valid Words", "Could not parse any valid words from input.")
            return
        
        # Start generation in background thread
        self.is_processing = True
        self.generate_btn.config(state=tk.DISABLED)
        self.progress_bar.start()
        self.progress_var.set(f"Processing {len(words)} words...")
        self._log(f"\n=== Starting generation of {len(words)} words ===")
        
        thread = threading.Thread(
            target=self._generate_wav_files,
            args=(words,),
            daemon=True
        )
        thread.start()
    
    def _generate_wav_files(self, words: list):
        """Generate WAV files for all words (runs in background thread)"""
        success_count = 0
        error_count = 0
        
        try:
            for i, word in enumerate(words, 1):
                if not self.is_processing:  # Check if cancelled
                    break
                
                # Update progress
                self.root.after(0, lambda w=word, idx=i, total=len(words): 
                    self.progress_var.set(f"Processing: {w} ({idx}/{total})"))
                self.root.after(0, lambda: self._log(f"[{i}/{len(words)}] Processing: {word}"))
                
                try:
                    # Get output path
                    output_path = get_output_path(self.output_dir, word)
                    
                    # Generate WAV file
                    self.tts_generator.generate_wav(word, output_path)
                    
                    success_count += 1
                    self.root.after(0, lambda p=output_path: 
                        self._log(f"  ✓ Saved: {os.path.basename(p)}"))
                    
                except Exception as e:
                    error_count += 1
                    error_msg = str(e)
                    self.root.after(0, lambda w=word, msg=error_msg: 
                        self._log(f"  ✗ Error for '{w}': {msg}"))
        
        except Exception as e:
            error_msg = f"Fatal error during generation: {str(e)}"
            self.root.after(0, lambda: self._log(f"  ✗ {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("Generation Error", error_msg))
        
        finally:
            # Update UI on main thread
            self.root.after(0, self._generation_complete, success_count, error_count, len(words))
    
    def _generation_complete(self, success_count: int, error_count: int, total_count: int):
        """Called when generation is complete"""
        self.is_processing = False
        self.progress_bar.stop()
        self.generate_btn.config(state=tk.NORMAL)
        
        # Show completion message
        if success_count == total_count:
            self.progress_var.set(f"Complete! Generated {success_count} WAV files.")
            self._log(f"\n=== Generation complete: {success_count} files created ===")
            messagebox.showinfo(
                "Generation Complete",
                f"Successfully generated {success_count} WAV files!\n\n"
                f"Output directory: {self.output_dir}"
            )
        else:
            self.progress_var.set(
                f"Complete: {success_count} succeeded, {error_count} failed"
            )
            self._log(
                f"\n=== Generation complete: {success_count} succeeded, {error_count} failed ==="
            )
            messagebox.showwarning(
                "Generation Complete with Errors",
                f"Generated {success_count} out of {total_count} WAV files.\n\n"
                f"{error_count} errors occurred. Check the status log for details."
            )
    
    def _on_closing(self):
        """Handle window closing"""
        if self.is_processing:
            if messagebox.askokcancel("Quit", "Generation in progress. Cancel and quit?"):
                self.is_processing = False
                if self.tts_generator:
                    self.tts_generator.cleanup()
                self.root.destroy()
        else:
            if self.tts_generator:
                self.tts_generator.cleanup()
            self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk()
    app = EnglishWhispererApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
