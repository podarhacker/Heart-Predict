from http.server import BaseHTTPRequestHandler
import json
import os
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, StratifiedKFold
from xgboost import XGBClassifier

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH  = os.path.join(BASE, 'heart_model.pkl')
SCALER_PATH = os.path.join(BASE, 'scaler.pkl')
FEATURES_PATH = os.path.join(BASE, 'feature_names.pkl')
DATA_PATH   = os.path.join(BASE, 'heart.csv')

# Vercel functions write to /tmp — the only writable directory
TMP_MODEL   = '/tmp/heart_model.pkl'
TMP_SCALER  = '/tmp/scaler.pkl'
TMP_FEATS   = '/tmp/feature_names.pkl'

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
            length       = int(self.headers.get('Content-Length', 0))
            body         = self.rfile.read(length)
            data         = json.loads(body)
            n_estimators = int(data.get('n_estimators', 600))
            random_state = int(data.get('random_state', 42))

            df = pd.read_csv(DATA_PATH)
            df = add_features(df)
            X  = df.drop('target', axis=1)
            y  = df['target']

            scaler   = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            model = XGBClassifier(
                n_estimators=n_estimators, learning_rate=0.01,
                max_depth=7, subsample=0.8, colsample_bytree=1.0,
                gamma=0.1, random_state=random_state,
                eval_metric='logloss', verbosity=0
            )
            cv     = StratifiedKFold(n_splits=10, shuffle=True, random_state=random_state)
            scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy')
            model.fit(X_scaled, y)

            # Save to /tmp (only writable dir on Vercel)
            joblib.dump(model,              TMP_MODEL)
            joblib.dump(scaler,             TMP_SCALER)
            joblib.dump(X.columns.tolist(), TMP_FEATS)

            fi = dict(sorted(
                zip(X.columns.tolist(), model.feature_importances_.tolist()),
                key=lambda x: x[1], reverse=True
            ))

            self._json(200, {
                'accuracy':        round(scores.mean() * 100, 2),
                'samples_trained': len(X),
                'total_samples':   len(df),
                'feature_importance': fi,
                'note': 'Model saved to /tmp. It will reset on next cold start. Commit your .pkl files to the repo for persistence.'
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
