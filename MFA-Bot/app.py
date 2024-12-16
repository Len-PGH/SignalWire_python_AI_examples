import os
import logging
import subprocess
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from signalwire.rest import Client as SignalWireClient
from signalwire_swaig.core import SWAIG, SWAIGArgument
import re
import json

# =======================
# Configuration and Setup
# =======================

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('signalwire').setLevel(logging.DEBUG)

load_dotenv()

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

PROJECT_ID = os.getenv("SIGNALWIRE_PROJECT_ID")
TOKEN = os.getenv("SIGNALWIRE_TOKEN")
SPACE = os.getenv("SIGNALWIRE_SPACE")
FROM_NUMBER = os.getenv("FROM_NUMBER")
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN")
NGROK_PATH = os.getenv("NGROK_PATH")
HTTP_USERNAME = os.getenv("HTTP_USERNAME")
HTTP_PASSWORD = os.getenv("HTTP_PASSWORD")

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
        """
        Sends MFA code using {code} so user receives the code in the SMS.
        """
        try:
            url = f"{self.base_url}/mfa/sms"
            payload = {
                "to": to_number,
                "from": self.from_number,
                "message": "Here is your code: {code}",
                "token_length": 6,
                "max_attempts": 3,
                "allow_alphas": False,
                "valid_for": 3600
            }
            headers = {"Content-Type": "application/json"}
            logging.debug(f"Sending MFA from {self.from_number} to {to_number}")
            logging.debug(f"Payload: {payload}")
            response = requests.post(
                url,
                json=payload,
                auth=(self.project_id, self.token),
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            logging.debug(f"Sent MFA code to {to_number}, Response: {data}")
            return data
        except Exception as e:
            logging.error(f"Error sending MFA code: {e}")
            raise

    def verify_mfa(self, mfa_id: str, token: str) -> dict:
        """
        Verifies the MFA code using mfa_id and token.
        Expect 'success': true if correct token, false otherwise.
        """
        try:
            verify_url = f"{self.base_url}/mfa/{mfa_id}/verify"
            payload = {"token": token}
            headers = {"Content-Type": "application/json"}
            logging.debug(f"Verifying MFA with ID {mfa_id} using token {token}")
            response = requests.post(
                verify_url,
                json=payload,
                auth=(self.project_id, self.token),
                headers=headers
            )
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

        if response.get("success") is True:
            return {"success": True, "message": "6 digit number sent", "data": {}}, 200
        else:
            return {"success": False}, 401
    except Exception as e:
        logging.error(f"Error sending MFA code: {e}")
        return {"success": False}, 500

@swaig.endpoint(
    "Verify an MFA code using token.",
    token=SWAIGArgument("string", "The 6-digit code from SMS", required=True)
)
def verify_mfa_code(token: str, meta_data: dict = None, **kwargs) -> dict:
    """
    Verifies the MFA code using the token only. The returned response is exactly what verify_mfa returns.
    The 'response' is now the result of mfa_util.verify_mfa(LAST_MFA_ID, token).
    """
    global LAST_MFA_ID
    logging.debug(f"Received token: {token}")

    if not LAST_MFA_ID or not is_valid_uuid(LAST_MFA_ID):
        logging.error("No valid mfa_id stored or send_mfa_code not called first.")
        # Return a failure response if no mfa_id or invalid mfa_id
        failure_response = {"success": False, "message": "No valid MFA session."}
        return failure_response, 401

    try:
        # Get the actual verification response from verify_mfa
        verification_response = mfa_util.verify_mfa(LAST_MFA_ID, token)
        logging.debug(f"Full verify_mfa response: {verification_response}")

        # If success is True, return as is with 200, else 401
        if verification_response.get("success") is True:
            return verification_response, 200
        else:
            return verification_response, 401
    except Exception as e:
        logging.error(f"Error verifying MFA code: {e}")
        # On internal error, return a generic failure response with 500
        error_response = {"success": False, "message": "Internal error"}
        return error_response, 500

@swaig.endpoint(
    "MFA failed response",
    response=SWAIGArgument("object", "This parameter should be {'success': False, 'message': 'HTTP error during verification.'}", required=True)
)
def mfa_failed_response(response: dict, meta_data: dict = None, **kwargs) -> dict:
    """
    Returns a hardcoded failed response for MFA verification.
    
    Parameters:
      response (object): Should be {'success': False, 'message': 'HTTP error during verification.'}
      
    Description:
      Simulates a verification failure scenario by returning this response object.
    """
    return response, 200

@swaig.endpoint(
    "MFA success response",
    response=SWAIGArgument("object", "This parameter should be {'success': True}", required=True)
)
def mfa_success_response(response: dict, meta_data: dict = None, **kwargs) -> dict:
    """
    Returns a hardcoded success response for MFA verification.
    
    Parameters:
      response (object): Should be {'success': True}
      
    Description:
      Simulates a verification success scenario by returning this response object.
    """
    return response, 200

@app.route("/swaig", methods=["POST", "GET"])
def handle_swaig():
    if request.method == "POST":
        data = request.get_json() or {}
        action = data.get("action")
        function_name = data.get("function")
        logging.debug(f"Handling request at /swaig with action: {action}, function: {function_name}")

        if action == "get_signature":
            signatures = swaig.get_signatures()
            logging.debug("Returning SWAIG signatures.")
            return jsonify(signatures)

        if not function_name:
            logging.error("Function name not provided.")
            return jsonify({"response": "Function name not provided."}), 400

        logging.debug(f"Delegating to SWAIG handler for function: {function_name}")
        return swaig.handle_request(data)
    else:
        # GET request returns signatures for convenience
        signatures = swaig.get_signatures()
        logging.debug("Returning SWAIG signatures via GET.")
        return jsonify(signatures)

if __name__ == "__main__":
    try:
        subprocess.run(
            [NGROK_PATH, "config", "add-authtoken", NGROK_AUTH_TOKEN],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        logging.debug("Ngrok auth token configured successfully.")

        ngrok_cmd = [
            NGROK_PATH,
            "http",
            "--domain=" + NGROK_DOMAIN,
            "5000"
        ]

        ngrok_process = subprocess.Popen(ngrok_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f" * Started ngrok tunnel at {NGROK_URL}")
        app.run(host="0.0.0.0", port=5000)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to configure ngrok: {e.stderr.decode().strip()}")
    except Exception as e:
        logging.error(f"Error starting ngrok or Flask app: {e}")
    finally:
        if 'ngrok_process' in locals():
            ngrok_process.terminate()
            logging.info("Ngrok process terminated.")