import os
import logging
import subprocess
import requests
import re
import json
import sqlite3

from flask import Flask, request, jsonify, g, render_template, redirect, url_for
from dotenv import load_dotenv
from signalwire.rest import Client as SignalWireClient
from signalwire_swaig.core import SWAIG, SWAIGArgument

# =======================
# Configuration and Setup
# =======================

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('werkzeug').setLevel(logging.DEBUG)
logging.getLogger('signalwire').setLevel(logging.DEBUG)

load_dotenv()

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
# SQLite database file for dental scheduling
app.config['DATABASE'] = os.path.join(app.root_path, 'calendar.db')

# Define API_TOKEN for dental scheduling endpoints.
API_TOKEN = os.getenv("API_TOKEN", "mysecrettoken")

# SignalWire and ngrok configuration (for MFA/SWAIG part)
PROJECT_ID = os.getenv("SIGNALWIRE_PROJECT_ID")
TOKEN = os.getenv("SIGNALWIRE_TOKEN")
SPACE = os.getenv("SIGNALWIRE_SPACE")
FROM_NUMBER = os.getenv("FROM_NUMBER")
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN")
NGROK_PATH = os.getenv("NGROK_PATH")
HTTP_USERNAME = os.getenv("HTTP_USERNAME")
HTTP_PASSWORD = os.getenv("HTTP_PASSWORD")
DEBUG_WEBOOK_URL = os.getenv("DEBUG_WEBOOK_URL")

required_vars = [
    "SIGNALWIRE_PROJECT_ID",
    "SIGNALWIRE_TOKEN",
    "SIGNALWIRE_SPACE",
    "FROM_NUMBER",
    "NGROK_AUTH_TOKEN",
    "NGROK_DOMAIN",
    "NGROK_PATH",
    "HTTP_USERNAME",
    "HTTP_PASSWORD"
]
missing_vars = [v for v in required_vars if os.getenv(v) is None]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

NGROK_URL = f"https://{NGROK_DOMAIN}"

logging.debug(f"SIGNALWIRE_SPACE: {SPACE}")
logging.debug(f"SIGNALWIRE_FROM_NUMBER: {FROM_NUMBER}")
logging.debug(f"NGROK_DOMAIN: {NGROK_DOMAIN}")
logging.debug(f"DEBUG_WEBOOK_URL: {DEBUG_WEBOOK_URL}")

# =======================
# Database Helper Functions
# =======================

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        # schema.sql must define patients, appointments (with patient_id), and visits
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# =======================
# Helper Functions
# =======================

def is_overlapping(new_start, new_end, exclude_id=None):
    """
    Check if the new appointment (new_start, new_end) overlaps any existing appointment.
    """
    db = get_db()
    query = "SELECT id FROM appointments WHERE (start_time < ? AND end_time > ?)"
    params = (new_end, new_start)
    if exclude_id:
        query += " AND id != ?"
        params += (exclude_id,)
    cursor = db.execute(query, params)
    return cursor.fetchone() is not None

def token_required(f):
    """A simple token-based decorator for protecting API endpoints."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', None)
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        if not token:
            token = request.args.get('token')
        if not token or token != API_TOKEN:
            return jsonify({'message': 'Token is missing or invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

# =======================
# SignalWire MFA & SWAIG Endpoints
# =======================

class SignalWireMFA:
    def __init__(self, project_id: str, token: str, space: str, from_number: str):
        try:
            self.client = SignalWireClient(project_id, token, signalwire_space_url=f"{space}.signalwire.com")
            self.project_id = project_id
            self.token = token
            self.space = space
            self.from_number = from_number
            self.base_url = f"https://{space}.signalwire.com/api/relay/rest"
            logging.debug(f"Initialized SignalWireMFA with from_number: {self.from_number}")
        except Exception as e:
            logging.error(f"Failed to initialize SignalWire Client: {e}")
            raise

    def send_mfa(self, to_number: str) -> dict:
        try:
            url = f"{self.base_url}/mfa/sms"
            payload = {
                "to": to_number,
                "from": self.from_number,
                "message": "Here is your code: ",
                "token_length": 6,
                "max_attempts": 3,
                "allow_alphas": False,
                "valid_for": 3600
            }
            headers = {"Content-Type": "application/json"}
            logging.debug(f"Sending MFA from {self.from_number} to {to_number}")
            response = requests.post(url, json=payload, auth=(self.project_id, self.token), headers=headers)
            response.raise_for_status()
            data = response.json()
            logging.debug(f"Sent MFA code to {to_number}, Response: {data}")
            return data
        except Exception as e:
            logging.error(f"Error sending MFA code: {e}")
            raise

    def verify_mfa(self, mfa_id: str, token: str) -> dict:
        try:
            verify_url = f"{self.base_url}/mfa/{mfa_id}/verify"
            payload = {"token": token}
            headers = {"Content-Type": "application/json"}
            logging.debug(f"Verifying MFA with ID {mfa_id} using token {token}")
            response = requests.post(verify_url, json=payload, auth=(self.project_id, self.token), headers=headers)
            response.raise_for_status()
            decoded_response = response.json()
            logging.debug(f"Verification response: {decoded_response}")
            return decoded_response
        except Exception as e:
            logging.error(f"Error during verification: {e}")
            return {"success": False, "message": "HTTP error during verification."}

mfa_util = SignalWireMFA(PROJECT_ID, TOKEN, SPACE, FROM_NUMBER)
swaig = SWAIG(app, auth=(HTTP_USERNAME, HTTP_PASSWORD))

def is_valid_uuid(uuid_to_test, version=4):
    regex = {
        1: r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$',
        4: r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'
    }
    pattern = regex.get(version)
    return bool(pattern and re.match(pattern, uuid_to_test))

LAST_MFA_ID = None

@swaig.endpoint(
    "Send an MFA code to a specified phone number.",
    to_number=SWAIGArgument("string", "Phone number in E.164 format", required=True)
)
def send_mfa_code(to_number: str, meta_data: dict = None, **kwargs) -> dict:
    global LAST_MFA_ID
    logging.debug(f"Attempting to send MFA code to {to_number}")
    try:
        response = mfa_util.send_mfa(to_number)
        mfa_id = response.get("id")
        if not mfa_id:
            raise ValueError("MFA ID not found in response.")
        LAST_MFA_ID = mfa_id
        logging.debug(f"Full send_mfa response: {response}")
        return {"success": True, "message": "6 digit number sent"}, 200
    except Exception as e:
        logging.error(f"Error sending MFA code: {e}")
        return {"success": False, "message": "Failed to send MFA code"}, 500

@swaig.endpoint(
    "Verify an MFA code using token.",
    token=SWAIGArgument("string", "The 6-digit code from SMS", required=True)
)
def verify_mfa_code(token: str, meta_data: dict = None, **kwargs) -> dict:
    global LAST_MFA_ID
    logging.debug(f"Received token: {token}")
    if not LAST_MFA_ID or not is_valid_uuid(LAST_MFA_ID):
        logging.error("No valid MFA session.")
        return {"success": False, "message": "No valid MFA session."}, 401
    try:
        verification_response = mfa_util.verify_mfa(LAST_MFA_ID, token)
        verification_response["mfa_id"] = LAST_MFA_ID
        logging.debug(f"Verification response: {verification_response}")
        if verification_response.get("success"):
           return {"success": False, "message": "Invalid MFA code. Please try again.", "mfa_id": LAST_MFA_ID}, 401

    except Exception as e:
        logging.error(f"Error verifying MFA code: {e}")
        return {"success": False, "message": "Internal server error occurred during verification."}, 500

@app.route("/swaig", methods=["POST", "GET"])
def handle_swaig():
    if request.method == "POST":
        data = request.get_json() or {}
        action = data.get("action")
        function_name = data.get("function")
        logging.debug(f"Handling /swaig request: action={action}, function={function_name}")
        if action == "get_signature":
            signatures = swaig.get_signatures()
            return jsonify(signatures)
        if not function_name:
            return jsonify({"response": "Function name not provided."}), 400
        return swaig.handle_request(data)
    else:
        signatures = swaig.get_signatures()
        return jsonify(signatures)

# =======================
# Dental Office Scheduling & Admin Endpoints
# =======================

# API Endpoints for Dental Appointments (Protected by token_required)
@app.route('/api/appointments', methods=['GET'])
@token_required
def api_get_appointments_dental():
    db = get_db()
    cursor = db.execute("""
        SELECT a.*,
               p.first_name,
               p.last_name,
               p.phone AS patient_phone,
               p.email AS patient_email
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
    """)
    appointments = [dict(row) for row in cursor.fetchall()]
    return jsonify(appointments)

@app.route('/api/appointments', methods=['POST'])
@token_required
def api_add_appointment_dental():
    data = request.get_json()
    required_fields = ["patient_id", "title", "start_time", "end_time"]
    if not data or not all(k in data for k in required_fields):
        return jsonify({'message': 'Missing required fields'}), 400
    start_time_str = data['start_time'].replace("T", " ")
    end_time_str = data['end_time'].replace("T", " ")
    if is_overlapping(start_time_str, end_time_str):
        return jsonify({'message': 'Appointment time conflicts with an existing appointment'}), 409
    patient_id = data['patient_id']
    title = data['title']
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO appointments (patient_id, title, start_time, end_time) VALUES (?, ?, ?, ?)",
        (patient_id, title, start_time_str, end_time_str)
    )
    db.commit()
    appointment_id = cursor.lastrowid
    return jsonify({'id': appointment_id, 'message': 'Appointment added'}), 201

@app.route('/api/appointments/<int:appointment_id>', methods=['PUT'])
@token_required
def api_update_appointment_dental(appointment_id):
    data = request.get_json()
    if not data or not any(k in data for k in ("title", "start_time", "end_time")):
        return jsonify({'message': 'Nothing to update'}), 400
    db = get_db()
    cursor = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    appointment = cursor.fetchone()
    if not appointment:
        return jsonify({'message': 'Appointment not found'}), 404
    new_start = data.get('start_time', appointment['start_time']).replace("T", " ")
    new_end = data.get('end_time', appointment['end_time']).replace("T", " ")
    if is_overlapping(new_start, new_end, exclude_id=appointment_id):
        return jsonify({'message': 'Appointment time conflicts with an existing appointment'}), 409
    title = data.get('title', appointment['title'])
    db.execute(
        "UPDATE appointments SET title = ?, start_time = ?, end_time = ? WHERE id = ?",
        (title, new_start, new_end, appointment_id)
    )
    db.commit()
    return jsonify({'message': 'Appointment updated'})

@app.route('/api/appointments/<int:appointment_id>', methods=['DELETE'])
@token_required
def api_delete_appointment_dental(appointment_id):
    db = get_db()
    cursor = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    appointment = cursor.fetchone()
    if not appointment:
        return jsonify({'message': 'Appointment not found'}), 404
    db.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    db.commit()
    return jsonify({'message': 'Appointment deleted'})

# API Endpoint for Searching Patients
@app.route('/api/patients/search', methods=['GET'])
def api_search_patients_dental():
    q = request.args.get('q', '')
    db = get_db()
    cursor = db.execute(
        "SELECT id, first_name, last_name FROM patients WHERE first_name LIKE ? OR last_name LIKE ? LIMIT 10",
        ('%' + q + '%', '%' + q + '%')
    )
    results = [dict(row) for row in cursor.fetchall()]
    return jsonify(results)

# Web Interface for Scheduling Appointments (For Current Patients Only)
@app.route('/add', methods=['GET', 'POST'])
def add_appointment():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        title = request.form['title']
        appointment_date = request.form['appointment_date']
        start_time_val = request.form['start_time']
        end_time_val = request.form['end_time']
        start_datetime = appointment_date + " " + start_time_val
        end_datetime = appointment_date + " " + end_time_val
        if is_overlapping(start_datetime, end_datetime):
            return "Error: Appointment time conflicts with an existing appointment", 409
        db = get_db()
        db.execute(
            "INSERT INTO appointments (patient_id, title, start_time, end_time) VALUES (?, ?, ?, ?)",
            (patient_id, title, start_datetime, end_datetime)
        )
        db.commit()
        return redirect(url_for('index'))
    return render_template('add_appointment.html')

@app.route('/move/<int:appointment_id>', methods=['GET', 'POST'])
def move_appointment_dental(appointment_id):
    db = get_db()
    cursor = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
    appointment = cursor.fetchone()
    if not appointment:
        return "Appointment not found", 404
    if request.method == 'POST':
        title = request.form.get('title', appointment['title'])
        appointment_date = request.form['appointment_date']
        start_time_val = request.form['start_time']
        end_time_val = request.form['end_time']
        start_datetime = appointment_date + " " + start_time_val
        end_datetime = appointment_date + " " + end_time_val
        if is_overlapping(start_datetime, end_datetime, exclude_id=appointment_id):
            return "Error: Appointment time conflicts with an existing appointment", 409
        db.execute(
            "UPDATE appointments SET title = ?, start_time = ?, end_time = ? WHERE id = ?",
            (title, start_datetime, end_datetime, appointment_id)
        )
        db.commit()
        return redirect(url_for('index'))
    return render_template('move_appointment.html', appointment=appointment)

@app.route('/delete/<int:appointment_id>', methods=['POST'])
def delete_appointment_dental(appointment_id):
    db = get_db()
    db.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    db.commit()
    return redirect(url_for('index'))

# Admin Section for Patients
@app.route('/admin/patients', methods=['GET'])
def admin_patients():
    db = get_db()
    cursor = db.execute("SELECT * FROM patients")
    patients = cursor.fetchall()
    return render_template('admin_patients.html', patients=patients)

@app.route('/admin/patients/add', methods=['GET', 'POST'])
def admin_add_patient():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = request.form.get('date_of_birth', '')
        gender = request.form.get('gender', '')
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        insurance = request.form.get('insurance', '')
        db = get_db()
        db.execute(
            "INSERT INTO patients (first_name, last_name, date_of_birth, gender, address, phone, email, insurance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (first_name, last_name, date_of_birth, gender, address, phone, email, insurance)
        )
        db.commit()
        return redirect(url_for('admin_patients'))
    return render_template('admin_add_patient.html')

# Admin Section for Patient Visits
@app.route('/admin/patients/<int:patient_id>/visits', methods=['GET'])
def admin_patient_visits(patient_id):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        return "Patient not found", 404
    cursor = db.execute("SELECT * FROM visits WHERE patient_id = ? ORDER BY visit_datetime DESC", (patient_id,))
    visits = cursor.fetchall()
    return render_template('admin_patient_visits.html', patient=patient, visits=visits)

@app.route('/admin/patients/<int:patient_id>/visits/add', methods=['GET', 'POST'])
def admin_add_patient_visit(patient_id):
    db = get_db()
    patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if not patient:
        return "Patient not found", 404
    if request.method == 'POST':
        visit_date = request.form['visit_date']
        visit_time = request.form['visit_time']
        visit_datetime = visit_date + " " + visit_time
        notes = request.form.get('notes', '')
        db.execute("INSERT INTO visits (patient_id, visit_datetime, notes) VALUES (?, ?, ?)",
                   (patient_id, visit_datetime, notes))
        db.commit()
        return redirect(url_for('admin_patient_visits', patient_id=patient_id))
    return render_template('admin_add_patient_visit.html', patient=patient)

# Root Calendar Interface
@app.route('/')
def index():
    return render_template('index.html', api_token=API_TOKEN)

# =======================
# Application Runner with Ngrok
# =======================
if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            init_db()
    try:
        subprocess.run(
            [NGROK_PATH, "config", "add-authtoken", NGROK_AUTH_TOKEN],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logging.debug("Ngrok auth token configured successfully.")
        ngrok_cmd = [NGROK_PATH, "http", "--domain=" + NGROK_DOMAIN, "8888"]
        ngrok_process = subprocess.Popen(ngrok_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f" * Started ngrok tunnel at {NGROK_URL}")
        app.run(host="0.0.0.0", port=8888, debug=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to configure ngrok: {e.stderr.decode().strip()}")
    except Exception as e:
        logging.error(f"Error starting ngrok or Flask app: {e}")
    finally:
        if 'ngrok_process' in locals():
            ngrok_process.terminate()
            logging.info("Ngrok process terminated.")
