from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

app = Flask(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE, 'heart_model.pkl')
SCALER_PATH = os.path.join(BASE, 'scaler.pkl')
FEATURES_PATH = os.path.join(BASE, 'feature_names.pkl')
DATA_PATH = os.path.join(BASE, 'heart.csv')

BASE_FEATURES = ['age','sex','cp','trestbps','chol','fbs','restecg','thalach','exang','oldpeak','slope','ca','thal']

def add_features(df):
    df = df.copy()
    df['age_thalach']   = df['age']      * df['thalach']
    df['bp_chol']       = df['trestbps'] * df['chol']
    df['oldpeak_slope'] = df['oldpeak']  * df['slope']
    df['cp_exang']      = df['cp']       * df['exang']
    return df

@app.after_request
def cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route('/api/model-status', methods=['GET','OPTIONS'])
def model_status():
    if request.method == 'OPTIONS': return jsonify({}), 200
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        return jsonify({'trained': True})
    return jsonify({'trained': False})

@app.route('/api/predict', methods=['POST','OPTIONS'])
def predict():
    if request.method == 'OPTIONS': return jsonify({}), 200
    try:
        data = request.json
        if not os.path.exists(MODEL_PATH):
            return jsonify({'error': 'Model not trained yet.'}), 400
        model  = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)

        row = {k: float(data[k]) for k in BASE_FEATURES}
        df_row = pd.DataFrame([row])
        df_row = add_features(df_row)

        X_s = scaler.transform(df_row)
        pred  = model.predict(X_s)[0]
        proba = model.predict_proba(X_s)[0]

        return jsonify({
            'prediction': int(pred),
            'label': 'Heart Disease Detected' if pred == 1 else 'No Heart Disease',
            'confidence': round(float(max(proba)) * 100, 2),
            'probability_positive': round(float(proba[1]) * 100, 2),
            'probability_negative': round(float(proba[0]) * 100, 2),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/train', methods=['POST','OPTIONS'])
def train():
    if request.method == 'OPTIONS': return jsonify({}), 200
    try:
        data = request.json
        n_estimators  = int(data.get('n_estimators', 600))
        test_size     = float(data.get('test_size', 0.2))
        random_state  = int(data.get('random_state', 42))

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

        joblib.dump(model,            MODEL_PATH)
        joblib.dump(scaler,           SCALER_PATH)
        joblib.dump(X.columns.tolist(), FEATURES_PATH)

        fi = dict(sorted(zip(X.columns.tolist(), model.feature_importances_.tolist()), key=lambda x: x[1], reverse=True))

        return jsonify({
            'accuracy':        round(scores.mean() * 100, 2),
            'samples_trained': len(X),
            'samples_tested':  int(len(X) * test_size),
            'total_samples':   len(df),
            'feature_importance': fi
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
