from flask import Flask, render_template_string, request, jsonify
import threading
import socket
import pyaudio
import struct
import time

app = Flask(__name__)

RTP_IP = "0.0.0.0"
RTP_PORT = 5004

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000

running = False
active_ssrcs = {}
listen_ssrc = None

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
    120, -112, -104, -96, -88, -80, -72, -64,
    -56, -48, -40, -32, -24, -16, -8, 0
]

def listen_rtp():
    global running, active_ssrcs, listen_ssrc
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((RTP_IP, RTP_PORT))
    sock.settimeout(1)

    while running:
        try:
            data, addr = sock.recvfrom(2048)
            rtp_header = data[:12]
            ssrc = struct.unpack('!I', rtp_header[8:12])[0]

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

            if ssrc == listen_ssrc:
                pcmu_payload = data[12:]
                pcm_samples = [ULAW_TO_PCM_TABLE[byte] for byte in pcmu_payload]
                pcm_bytes = struct.pack(f"<{len(pcm_samples)}h", *pcm_samples)
                stream.write(pcm_bytes)

        except socket.timeout:
            continue

    stream.stop_stream()
    stream.close()
    audio.terminate()
    sock.close()

@app.route('/')
def index():
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>RTP Listener</title>
        <!-- Bootstrap CSS -->
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
            setInterval(async () => {
                const response = await fetch('/ssrc');
                const data = await response.json();
                document.getElementById('ssrc_table').innerHTML = data.html;
            }, 2000);
            function listen(ssrc) {
                fetch('/listen/' + ssrc, {method: 'POST'});
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
    global listen_ssrc
    listen_ssrc = None if listen_ssrc == ssrc else ssrc
    return jsonify({"status": "updated", "listening_ssrc": listen_ssrc})

@app.route('/start', methods=['POST'])
def start_listening():
    global running
    if not running:
        running = True
        threading.Thread(target=listen_rtp, daemon=True).start()
    return jsonify({"status": "started"})

@app.route('/stop', methods=['POST'])
def stop_listening():
    global running
    running = False
    return jsonify({"status": "stopped"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
