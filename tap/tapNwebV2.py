from flask import Flask, render_template_string, request, jsonify, Response
import threading
import socket
import struct
import time
from queue import Queue

app = Flask(__name__)

# Configuration
RTP_IP = "0.0.0.0"  # Listen on all interfaces
RTP_PORT = 5004     # RTP port to receive packets

# Global variables
running = False
active_ssrcs = {}   # Dictionary to track SSRCs and their metadata
listen_ssrc = None  # Currently selected SSRC for listening
audio_queue = Queue()  # Queue to hold PCM audio data for streaming

# μ-law to PCM conversion table (G.711 μ-law to 16-bit linear PCM)
ULAW_TO_PCM_TABLE = [
    -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
    -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
    -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
    -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
    -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
    -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
    -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
    -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
    -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
    -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
    -876, -844, -812, -780, -748, -716, -684, -652,
    -620, -588, -556, -524, -492, -460, -428, -396,
    -372, -356, -340, -324, -308, -292, -276, -260,
    -244, -228, -212, -196, -180, -164, -148, -132,
    -120, -112, -104, -96, -88, -80, -72, -64,
    -56, -48, -40, -32, -24, -16, -8, 0,
    32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
    23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
    15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
    11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
    7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
    5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
    3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
    2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
    1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
    1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
    876, 844, 812, 780, 748, 716, 684, 652,
    620, 588, 556, 524, 492, 460, 428, 396,
    372, 356, 340, 324, 308, 292, 276, 260,
    244, 228, 212, 196, 180, 164, 148, 132,
    120, 112, 104, 96, 88, 80, 72, 64,
    56, 48, 40, 32, 24, 16, 8, 0
]

def listen_rtp():
    """Receive RTP packets and process audio for the selected SSRC."""
    global running, active_ssrcs, listen_ssrc
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((RTP_IP, RTP_PORT))
    sock.settimeout(1)

    while running:
        try:
            data, addr = sock.recvfrom(2048)
            if len(data) < 12:  # Minimum RTP header size
                continue
            rtp_header = data[:12]
            ssrc = struct.unpack('!I', rtp_header[8:12])[0]

            # Update SSRC metadata
            if ssrc not in active_ssrcs:
                active_ssrcs[ssrc] = {
                    "packet_count": 0,
                    "first_seen": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                    "last_seen": None,
                    "source_ip": addr[0],
                    "source_port": addr[1],
                }

            active_ssrcs[ssrc]["packet_count"] += 1
            active_ssrcs[ssrc]["last_seen"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

            # Process audio for the selected SSRC
            if ssrc == listen_ssrc:
                pcmu_payload = data[12:]  # Extract payload after RTP header
                print(f"Processing audio for SSRC {ssrc}, payload length: {len(pcmu_payload)}")
                pcm_samples = [ULAW_TO_PCM_TABLE[byte] for byte in pcmu_payload]
                pcm_bytes = struct.pack(f"<{len(pcm_samples)}h", *pcm_samples)
                print(f"Putting {len(pcm_bytes)} bytes into audio_queue")
                audio_queue.put(pcm_bytes)

        except socket.timeout:
            continue

    sock.close()

def create_wav_header():
    """Generate a WAV header for streaming audio."""
    sample_rate = 8000
    bits_per_sample = 16
    num_channels = 1
    block_align = num_channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align

    header = (
        b'RIFF' +
        struct.pack('<I', 0xFFFFFFFF) +  # RIFF chunk size (unknown for streaming)
        b'WAVE' +
        b'fmt ' +
        struct.pack('<I', 16) +          # fmt chunk size
        struct.pack('<HHIIHH', 1, num_channels, sample_rate, byte_rate, block_align, bits_per_sample) +
        b'data' +
        struct.pack('<I', 0xFFFFFFFF)    # data chunk size (unknown for streaming)
    )
    return header

@app.route('/stream.wav')
def stream_wav():
    """Stream audio data as a WAV file to the browser."""
    def generate():
        yield create_wav_header()
        while True:
            try:
                data = audio_queue.get(timeout=1)
                yield data
            except Queue.Empty:
                continue
    return Response(generate(), mimetype='audio/wav')

@app.route('/')
def index():
    """Render the main page with SSRC table and controls."""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>RTP Listener</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                background: linear-gradient(135deg, #007bff, #6c757d);
                color: white;
            }
            .btn-custom {
                background-color: #0056b3;
                border-color: #0056b3;
                color: white;
            }
            .btn-custom:hover {
                background-color: #004085;
                border-color: #004085;
                color: white;
            }
            table {
                background-color: rgba(255,255,255,0.9);
                color: black;
            }
        </style>
        <script>
            let currentAudio = null;

            // Update SSRC table every 2 seconds
            setInterval(async () => {
                const response = await fetch('/ssrc');
                const data = await response.json();
                document.getElementById('ssrc_table').innerHTML = data.html;
            }, 2000);

            // Handle Listen button click to select SSRC and control audio
            function listen(ssrc) {
                fetch('/listen/' + ssrc, {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        if (data.listening_ssrc) {
                            if (currentAudio) {
                                currentAudio.pause();
                            }
                            currentAudio = new Audio('/stream.wav');
                            currentAudio.play().catch(e => console.log("Play error:", e));
                        } else {
                            if (currentAudio) {
                                currentAudio.pause();
                            }
                        }
                    });
            }
        </script>
    </head>
    <body class="container py-5">
        <h2>RTP Listener Control</h2>
        <div class="mb-3">
            <button class="btn btn-custom me-2" onclick="fetch('/start', {method: 'POST'})">Start Listening</button>
            <button class="btn btn-custom" onclick="fetch('/stop', {method: 'POST'})">Stop Listening</button>
        </div>
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>SSRC</th>
                    <th>Packets Received</th>
                    <th>First Seen</th>
                    <th>Last Activity</th>
                    <th>Source IP</th>
                    <th>Source Port</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody id="ssrc_table"></tbody>
        </table>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/ssrc')
def get_ssrc():
    """Return HTML for the SSRC table."""
    rows = ''.join(
        f'<tr>'
        f'<td>{ssrc}</td>'
        f'<td>{info["packet_count"]}</td>'
        f'<td>{info["first_seen"]}</td>'
        f'<td>{info["last_seen"]}</td>'
        f'<td>{info["source_ip"]}</td>'
        f'<td>{info["source_port"]}</td>'
        f'<td><button class="btn btn-sm btn-custom" onclick="listen({ssrc})">{"Listening" if ssrc == listen_ssrc else "Listen"}</button></td>'
        f'</tr>'
        for ssrc, info in active_ssrcs.items()
    )
    return jsonify({"html": rows})

@app.route('/listen/<int:ssrc>', methods=['POST'])
def select_ssrc(ssrc):
    """Toggle the selected SSRC for listening."""
    global listen_ssrc
    listen_ssrc = None if listen_ssrc == ssrc else ssrc
    return jsonify({"status": "updated", "listening_ssrc": listen_ssrc})

@app.route('/start', methods=['POST'])
def start_listening():
    """Start the RTP listener thread."""
    global running
    if not running:
        running = True
        threading.Thread(target=listen_rtp, daemon=True).start()
    return jsonify({"status": "started"})

@app.route('/stop', methods=['POST'])
def stop_listening():
    """Stop the RTP listener."""
    global running
    running = False
    return jsonify({"status": "stopped"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
