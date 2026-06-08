from http.server import BaseHTTPRequestHandler
import json, os
import numpy as np
import pandas as pd
import joblib

BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH  = os.path.join(BASE, 'heart_model.pkl')
SCALER_PATH = os.path.join(BASE, 'scaler.pkl')
TMP_MODEL   = '/tmp/heart_model.pkl'
TMP_SCALER  = '/tmp/scaler.pkl'

BASE_FEATURES = ['age','sex','cp','trestbps','chol','fbs','restecg',
                 'thalach','exang','oldpeak','slope','ca','thal']

def add_features(df):
    df = df.copy()
    df['age_thalach']   = df['age']      * df['thalach']
    df['bp_chol']       = df['trestbps'] * df['chol']
    df['oldpeak_slope'] = df['oldpeak']  * df['slope']
    df['cp_exang']      = df['cp']       * df['exang']
    return df

def load_model():
    # Prefer /tmp (retrained this session) over repo model
    m_path = TMP_MODEL   if os.path.exists(TMP_MODEL)   else MODEL_PATH
    s_path = TMP_SCALER  if os.path.exists(TMP_SCALER)  else SCALER_PATH
    if os.path.exists(m_path) and os.path.exists(s_path):
        return joblib.load(m_path), joblib.load(s_path)
    return None, None

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            data   = json.loads(self.rfile.read(length))
            model, scaler = load_model()

            if model is None:
                self._json(400, {'error': 'Model not found. Commit heart_model.pkl to your repo.'}); return

            row    = {k: float(data[k]) for k in BASE_FEATURES}
            df_row = add_features(pd.DataFrame([row]))
            X_s    = scaler.transform(df_row)
            pred   = model.predict(X_s)[0]
            proba  = model.predict_proba(X_s)[0]

            self._json(200, {
                'prediction':           int(pred),
                'label':                'Heart Disease Detected' if pred == 1 else 'No Heart Disease',
                'confidence':           round(float(max(proba))   * 100, 2),
                'probability_positive': round(float(proba[1])     * 100, 2),
                'probability_negative': round(float(proba[0])     * 100, 2),
            })
        except Exception as e:
            self._json(500, {'error': str(e)})

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def _json(self, code, body):
        self.send_response(code); self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
