# Listening to RTP Audio Streams with Python and SWML

<img src="https://github.com/user-attachments/assets/11558fc8-9fc5-449d-9a9a-4f495f9d140b" alt="image" style="width:20%;">


**Table of Contents**

- [Core Functionality](#core-functionality)
- [Windows Version](#windows-version)
- [Mac Version](#mac-version)
- [Why Two Scripts?](#why-two-scripts)
- [How to Use](#how-to-use)
- [Utilizing the `tap` Method in SWML](#utilizing-the-tap-method-in-swml)

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

The Windows script (`setup-win.py`) uses the `msvcrt` module, exclusive to Windows, for non-blocking keyboard input.

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

The Unix/Mac script (`setup-mac.py`) uses `termios` and `tty` modules, standard on Unix-like systems (e.g., macOS, Linux), for keyboard input in raw mode.

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

Separate scripts ensure optimal performance on each platform. The key difference—keyboard input handling—stems from how Windows and Unix-like systems manage terminal I/O.

---

## How to Use

- **Run the Script**: Execute it in a Windows command prompt or terminal.
- **Controls**:
  - **Left Arrow**: Switch to the previous active SSRC.
  - **Right Arrow**: Switch to the next active SSRC.
  - **'q'**: Exit the script.
- **Requirements**: Ensure PyAudio is installed (`pip install pyaudio`) and your system has an audio output device.

---

## Utilizing the `tap` Method in SWML

The `tap` method in SignalWire Markup Language (SWML) enables developers to stream call audio to an external destination via WebSocket or RTP. This functionality is essential for applications requiring real-time audio processing, such as call monitoring or recording.

### Key Parameters

- **uri** (string, required): Specifies the destination for the audio stream. Supported formats include:
  - `rtp://IP:port`
  - `ws://example.com`
  - `wss://example.com`

- **control_id** (string, optional): An identifier for the tap session, useful for managing or stopping the tap later. If not provided, a unique ID is auto-generated and stored in the `tap_control_id` variable.

- **direction** (string, optional): Defines which part of the audio to tap:
  - `speak`: Audio sent from the party.
  - `listen`: Audio received by the party.
  - `both`: Both incoming and outgoing audio.

  Default is `speak`.

- **codec** (string, optional): Specifies the audio codec, either `PCMU` or `PCMA`. Default is `PCMU`.

- **rtp_ptime** (integer, optional): Applicable for RTP streams; sets the packetization time in milliseconds. Default is 20 ms.

### Example Usage

To initiate a (RTP) tap:

```json
{
  "version": "1.0.0",
  "sections": {
    "main": [
      {
        "tap": {
          "uri": "rtp://IP:port/tap"
        }
      }
    ]
  }
}
