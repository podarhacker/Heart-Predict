from http.server import BaseHTTPRequestHandler
import json
import os

BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH  = os.path.join(BASE, 'heart_model.pkl')
TMP_MODEL   = '/tmp/heart_model.pkl'

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        # Check repo model first, then /tmp (trained this session)
        trained = os.path.exists(MODEL_PATH) or os.path.exists(TMP_MODEL)
        source  = 'repo' if os.path.exists(MODEL_PATH) else ('session' if os.path.exists(TMP_MODEL) else None)
        self._json(200, {'trained': trained, 'source': source})

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def _json(self, code, body):
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
