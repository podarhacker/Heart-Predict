from http.server import BaseHTTPRequestHandler
import json
import os
import numpy as np
import joblib
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH  = os.path.join(BASE, 'heart_model.pkl')
SCALER_PATH = os.path.join(BASE, 'scaler.pkl')

BASE_FEATURES = ['age','sex','cp','trestbps','chol','fbs','restecg',
                 'thalach','exang','oldpeak','slope','ca','thal']

def add_features(df):
    df = df.copy()
    df['age_thalach']   = df['age']      * df['thalach']
    df['bp_chol']       = df['trestbps'] * df['chol']
    df['oldpeak_slope'] = df['oldpeak']  * df['slope']
    df['cp_exang']      = df['cp']       * df['exang']
    return df

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)

            if not os.path.exists(MODEL_PATH):
                self._json(400, {'error': 'Model not found. Include heart_model.pkl in your repo.'})
                return

            model  = joblib.load(MODEL_PATH)
            scaler = joblib.load(SCALER_PATH)

            row    = {k: float(data[k]) for k in BASE_FEATURES}
            df_row = pd.DataFrame([row])
            df_row = add_features(df_row)
            X_s    = scaler.transform(df_row)

            pred   = model.predict(X_s)[0]
            proba  = model.predict_proba(X_s)[0]

            self._json(200, {
                'prediction':           int(pred),
                'label':                'Heart Disease Detected' if pred == 1 else 'No Heart Disease',
                'confidence':           round(float(max(proba)) * 100, 2),
                'probability_positive': round(float(proba[1])   * 100, 2),
                'probability_negative': round(float(proba[0])   * 100, 2),
            })
        except Exception as e:
            self._json(500, {'error': str(e)})

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def _json(self, code, body):
        self.send_response(code)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
