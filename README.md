# English Whisperer

A cross-platform desktop application that generates WAV audio files from words using high-quality text-to-speech (TTS). Supports English and German languages. Perfect for creating audio files for language learning, accessibility, or any project requiring word-to-speech conversion.

## Features

### Core Features
- **Cross-platform**: Works on Linux, Windows, and macOS
- **High-Quality TTS**: Uses Microsoft Edge TTS (neural voices) by default for natural-sounding speech
- **Multi-language Support**: Supports English and German (Deutsch)
- **Voice Selection**: Choose from multiple available voices for each language
- **Speed Control**: Adjustable speech rate (75-150 words per minute)
- **Offline Fallback**: Automatically falls back to system TTS (pyttsx3) if internet is unavailable
- **Batch Processing**: Generate multiple WAV files from a word list

### User Interface
- **Modern GUI**: Built with Qt (PySide6) with clean, intuitive design
- **Drag & Drop**: Drop text files directly onto the app to load word lists
- **Live Word Count**: See how many words will be processed as you type
- **Audio Preview**: Test voice and speed settings before bulk generation
- **Recent Directories**: Quick access to recently used output folders
- **Compact Mode**: Optional condensed layout for smaller screens
- **Save/Load Word Lists**: Save your word lists for reuse
- **Keyboard Shortcuts**: Full keyboard navigation support
- **Progress Tracking**: Real-time progress updates and status logging
- **Error Handling**: Robust error handling with detailed feedback

## Requirements

### System Dependencies

**For online TTS (Edge TTS - recommended, high quality):**
- Internet connection (for Microsoft Edge TTS)
- **ffmpeg** (required for audio conversion from MP3 to WAV)

  **Windows:**
  ```powershell
  # Option 1: Using Chocolatey
  choco install ffmpeg

  # Option 2: Manual installation
  # 1. Download from https://github.com/BtbN/FFmpeg-Builds/releases
  # 2. Extract to C:\ffmpeg
  # 3. Add C:\ffmpeg\bin to system PATH
  ```

  **Linux:**
  ```bash
  # Ubuntu/Debian
  sudo apt-get install ffmpeg

  # Fedora
  sudo dnf install ffmpeg

  # Arch Linux
  sudo pacman -S ffmpeg
  ```

  **macOS:**
  ```bash
  brew install ffmpeg
  ```

**For offline TTS (pyttsx3 fallback):**

**Linux:**
- `espeak` or `espeak-ng` (text-to-speech engine)
  ```bash
  # Ubuntu/Debian
  sudo apt-get install espeak espeak-data

  # Fedora
  sudo dnf install espeak espeak-devel

  # Arch Linux
  sudo pacman -S espeak
  ```

**Windows:**
- SAPI5 (usually pre-installed with Windows)
- If not available, install Microsoft Speech Platform SDK

### Python Dependencies

- Python 3.8 or higher
- `uv` (fast Python package installer)
- `edge-tts` (Microsoft Edge TTS - high quality neural voices, requires internet)
- `pyttsx3` (Offline fallback TTS engine)
- `PySide6` (Qt GUI framework with multimedia support for audio preview)
- `pydub` (Audio processing for MP3 to WAV conversion)

## Installation

1. Clone or download this repository

2. Install `uv` (if not already installed):
   ```bash
   # Linux/macOS
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # Or via pip
   pip install uv
   ```

3. Install Python dependencies:
   ```bash
   uv sync
   ```

4. Ensure system TTS dependencies are installed (see Requirements above)

## Usage

### Running the Application

Using uv:
```bash
uv run python main.py
```

Or activate the virtual environment first:
```bash
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

python main.py
```

Or if installed as a package:
```bash
uv run python -m src.main
```

### Using the GUI

1. **Select Language**: Choose your language from the dropdown (English or German)

2. **Select Voice** (optional): Choose a specific voice from the dropdown. For Edge TTS, multiple neural voices are available. For system TTS, available voices depend on your system.

3. **Adjust Speed** (optional): Choose speech speed using radio buttons:
   - **Slower**: 75 WPM (slower, more deliberate speech)
   - **Normal**: 100 WPM (default, natural pace)
   - **Faster**: 150 WPM (quicker speech)

4. **Preview Voice** (optional): Click "🔊 Preview Voice" or press **Ctrl+P** to test the current voice and speed settings with sample text

5. **Enter Words**: Multiple ways to add words:
   - Type or paste directly in the text area
   - **Drag & drop** a `.txt` or `.csv` file onto the text area
   - Click **"Load from File..."** or press **Ctrl+O**
   - Words can be separated by newlines or commas
   - Live word count shows how many words will be processed

6. **Select Output Directory**:
   - Click "Browse..." to choose where WAV files will be saved
   - Use the dropdown menu to select from recently used directories

7. **Generate**: Click "Generate WAV Files" or press **Ctrl+G** to start processing

8. **Monitor Progress**: Watch the progress bar and status log for real-time updates

9. **Save Word List** (optional): Click "Save to File..." or press **Ctrl+S** to save your word list for later use

### Keyboard Shortcuts

- **Ctrl+G**: Generate WAV files
- **Ctrl+O**: Load word list from file
- **Ctrl+S**: Save word list to file
- **Ctrl+P**: Preview audio
- **Ctrl+L**: Clear word list
- **Ctrl+W**: Focus word list
- **Ctrl+Q**: Quit application

### Tips

- **Drag & Drop**: Simply drag a text file from your file manager onto the word list area to load it instantly
- **Recent Directories**: The app remembers your last 10 output directories for quick access
- **Compact Mode**: Enable via **View > Compact Mode** for a more condensed layout on smaller screens
- **Audio Preview**: Use the preview feature to test different voices and speeds before generating many files
- **Settings Persistence**: Your last output directory and compact mode preference are saved between sessions
- You can change language, voice, and speed at any time, but it's recommended to wait for the current generation to complete before changing settings

### Example Word List

```
hello
world
python
programming
language
```

Or comma-separated:
```
hello, world, python, programming, language
```

## Output

- Each word is saved as a separate WAV file
- Filenames are sanitized (special characters removed, spaces replaced with underscores)
- Files are saved in the selected output directory
- If a filename conflict occurs, a number is appended (e.g., `word_1.wav`)

## Project Structure

```
english-whisperer/
├── src/
│   ├── __init__.py
│   ├── main.py              # GUI application with drag & drop support
│   ├── tts_generator.py     # TTS engine wrapper
│   └── file_handler.py      # File I/O utilities
├── main.py                  # Entry point
├── pyproject.toml           # Project configuration (uv)
├── uv.lock                  # Lock file (auto-generated by uv, should be committed)
├── .venv/                   # Virtual environment (created by uv, gitignored)
└── README.md
```

**User Configuration:**
- Settings are saved to `~/.english_whisperer_config.json` (auto-created)
- Stores recent directories and compact mode preference
- No manual configuration needed

**Note:** The `uv.lock` file should be committed to the repository to ensure reproducible builds across different environments.

## Building Standalone Executables

To create standalone executables for distribution:

1. Install PyInstaller (if not already installed):
   ```bash
   uv add --dev pyinstaller
   ```

2. Build for your platform:
   ```bash
   # Linux
   pyinstaller --onefile --windowed main.py
   
   # Windows
   pyinstaller --onefile --windowed main.py
   ```

The executable will be in the `dist/` directory.

## Troubleshooting

### Audio Conversion Failed / MP3 to WAV Error

**Error:** "ffmpeg not found" or "Failed to load audio file from edge-tts"

**Solution:**
- **Windows:** Install ffmpeg and add it to your system PATH
  - Download from https://github.com/BtbN/FFmpeg-Builds/releases or use `choco install ffmpeg`
  - Verify installation: `ffmpeg -version` in Command Prompt
- **Linux:** Install ffmpeg using your package manager (see System Dependencies)
- **macOS:** Install via Homebrew: `brew install ffmpeg`

Edge TTS generates MP3 files that need to be converted to WAV format, which requires ffmpeg.

### TTS Engine Not Found

**For Edge TTS (recommended, high quality):**
- Ensure you have an internet connection
- Ensure ffmpeg is installed (see above)
- Edge TTS is free and uses Microsoft's neural voices
- If offline, the app will automatically fall back to system TTS

**For offline TTS (fallback):**
- **Linux:** Ensure `espeak` or `espeak-ng` is installed
  - Verify installation: `espeak --version`
- **Windows:** SAPI5 should be pre-installed
  - If issues occur, try installing Microsoft Speech Platform SDK

### No Audio Generated

- Check that the output directory is writable
- Verify words are not empty after parsing
- Check the status log for specific error messages
- Ensure ffmpeg is installed if using Edge TTS

### Application Won't Start

- Ensure Python 3.8+ is installed
- Verify all dependencies are installed: `uv sync`
- On Linux, ensure Qt libraries are available (usually installed with PySide6)
- If you see X11 errors, Qt should handle threading better than tkinter

### Audio Preview Not Working

**Issue:** Preview button doesn't play sound

**Solutions:**
- **Linux:** Ensure you have a working audio system (PulseAudio, ALSA, or PipeWire)
  - Test with: `aplay /usr/share/sounds/alsa/Front_Center.wav`
  - Install required packages: `sudo apt-get install libqt6multimedia6`
- **Windows:** Audio should work out of the box with Windows Media Foundation
- **macOS:** Audio should work with AVFoundation (built-in)
- Check system volume is not muted
- Try generating a file first to verify TTS is working, then test preview

### Drag & Drop Not Working

- Ensure the file has a `.txt`, `.csv`, or `.list` extension
- Try using "Load from File..." button instead
- Check file permissions (file must be readable)

## License

This project is open source and available for personal and commercial use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
