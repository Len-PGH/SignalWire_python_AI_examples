# Listening to RTP Audio Streams with Python: Windows and Unix/Mac Solutions

**Table of Contents**

- [Core Functionality](#core-functionality)
- [Windows Version](#windows-version)
- [Mac Version](#mac-version)
- [Why Two Scripts?](#why-two-scripts)

---

Below are two Python scripts designed to listen to Real-time Transport Protocol (RTP) audio streams, decode PCMU (μ-law) audio, and play it using PyAudio, with support for multiple streams. One script is tailored for Windows (`setup-win.py`), and the other for Unix/Mac systems (`setup-mac.py`). This guide explains their functionality and key differences.

---

## Core Functionality

Both scripts handle the following tasks:

- **RTP Packet Reception**:  
  Listens for UDP-based RTP packets on a specified IP and port (e.g., `0.0.0.0:5004`).
  
- **Audio Decoding**:  
  Converts PCMU audio (payload type 0) to 16-bit PCM using a μ-law lookup table for playback.

- **Multi-Stream Support**:  
  Tracks multiple Synchronization Sources (SSRCs) and allows switching between them with arrow keys.

- **Stream Cleanup**:  
  Removes inactive SSRCs after a 2-second timeout.

The scripts differ primarily in how they handle keyboard input, due to platform-specific requirements.

---

## Windows Version

The Windows script  (`setup-win.py`) uses the `msvcrt` module, which is exclusive to Windows, for non-blocking keyboard input.

### Key Features:
- **Keyboard Input**:  
  - `msvcrt.kbhit()` checks for key presses, and `msvcrt.getch()` reads them without blocking.  
  - Arrow keys are detected as two-byte sequences (e.g., `\x00` or `\xe0` followed by `K` for left or `M` for right).  
  - A small delay (`time.sleep(0.01)`) in the input thread reduces CPU usage while keeping the script responsive.

- **Setup Support**:  
  - Includes a batch file (`setup_and_run.bat`) that:  
    - Downloads Python (if not installed) using `bitsadmin`.  
    - Ensures `pip` is available.  
    - Installs dependencies like `pyaudio`.

This version is ideal for Windows users monitoring RTP audio streams, such as in VoIP debugging.

---

## Mac Version

The Unix/Mac  (`setup-mac.py`) script uses `termios` and `tty` modules, standard on Unix-like systems (e.g., macOS, Linux), for keyboard input in raw mode.

### Key Features:
- **Keyboard Input**:  
  - A custom `get_char()` function reads single characters from stdin using `termios` and `tty`.  
  - Arrow keys are detected via escape sequences (e.g., `\x1b[D` for left, `\x1b[C` for right).

- **Compatibility**:  
  - Runs natively on macOS and Linux, relying only on standard Python modules (plus PyAudio).  
  - Lightweight and doesn’t require Windows-specific libraries.

This version suits Unix/Mac users needing a reliable RTP audio solution.

---

## Why Two Scripts?

Separate scripts ensure optimal performance on each platform. The key difference—keyboard input handling—stems from how Windows and Unix-like systems manage terminal I/O. Whether you’re testing audio streams or troubleshooting VoIP, these scripts offer a tailored, effective solution for your platform.

---

How to Use

    Run the Script: Execute it in a Windows command prompt or terminal.
    Controls:
        Left Arrow: Switch to the previous active SSRC.
        Right Arrow: Switch to the next active SSRC.
        'q': Exit the script.
    Requirements: Ensure PyAudio is installed (pip install pyaudio) and that your system has an audio output device.
