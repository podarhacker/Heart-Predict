from http.server import BaseHTTPRequestHandler
import json, os
import pandas as pd
import joblib
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, StratifiedKFold

BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH   = os.path.join(BASE, 'heart.csv')
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
        self.send_response(200); self._cors(); self.end_headers()

    def do_POST(self):
        try:
            length       = int(self.headers.get('Content-Length', 0))
            data         = json.loads(self.rfile.read(length))
            n_estimators = int(data.get('n_estimators', 500))
            random_state = int(data.get('random_state', 42))

            df = add_features(pd.read_csv(DATA_PATH))
            X  = df.drop('target', axis=1)
            y  = df['target']

            scaler   = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            model  = ExtraTreesClassifier(
                n_estimators=n_estimators, max_depth=15,
                class_weight='balanced', random_state=random_state
            )
            cv     = StratifiedKFold(n_splits=10, shuffle=True, random_state=random_state)
            scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy')
            model.fit(X_scaled, y)

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
                'feature_importance': fi
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
