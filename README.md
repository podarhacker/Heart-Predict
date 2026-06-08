# CardioSense — Heart Disease Prediction Web App

A full-stack web app for heart disease prediction using XGBoost with engineered features.
Built with Flask (backend) + vanilla HTML/CSS/JS (frontend).

---

## File Structure

```
heart-app/
│
├── api/
│   └── predict.py              # Flask backend — all API routes
│                               # (predict, train, model-status)
│
├── public/
│   └── index.html              # Frontend — Predict + Train tabs
│
├── heart.csv                   # Cleveland Heart Disease dataset (303 rows)
├── heart_model.pkl             # Trained XGBoost model (83.15% CV accuracy)
├── scaler.pkl                  # StandardScaler fitted on training data
├── feature_names.pkl           # List of 17 feature names (13 original + 4 engineered)
│
├── requirements.txt            # Python dependencies
├── vercel.json                 # Vercel deployment config
└── README.md                   # This file
```

---

## Model Details

| Property | Value |
|---|---|
| Algorithm | XGBoost (tuned) |
| CV Accuracy (10-fold) | **83.15% ± 5.43%** |
| Dataset | Cleveland Heart Disease (303 samples) |
| Features | 17 (13 original + 4 engineered) |

### Features Used

**Original (13):**
| Feature | Description |
|---|---|
| age | Age in years |
| sex | 1 = Male, 0 = Female |
| cp | Chest pain type (0–3) |
| trestbps | Resting blood pressure (mm/Hg) |
| chol | Serum cholesterol (mg/dl) |
| fbs | Fasting blood sugar > 120 mg/dl (1/0) |
| restecg | Resting ECG results (0–2) |
| thalach | Max heart rate achieved |
| exang | Exercise induced angina (1/0) |
| oldpeak | ST depression induced by exercise |
| slope | Slope of peak exercise ST segment (0–2) |
| ca | Number of major vessels colored (0–3) |
| thal | Thalassemia type (1–3) |

**Engineered (4):**
| Feature | Formula | Why |
|---|---|---|
| age_thalach | age × thalach | Age-adjusted heart rate interaction |
| bp_chol | trestbps × chol | Combined cardiovascular pressure |
| oldpeak_slope | oldpeak × slope | ST segment combined signal |
| cp_exang | cp × exang | Chest pain + exertion interaction |

### XGBoost Hyperparameters
```
n_estimators   = 600
learning_rate  = 0.01
max_depth      = 7
subsample      = 0.8
colsample_bytree = 1.0
gamma          = 0.1
```

---

## API Endpoints

### `GET /api/model-status`
Returns whether a trained model exists.
```json
{ "trained": true }
```

### `POST /api/predict`
Send 13 patient features, get prediction back.

**Request:**
```json
{
  "age": 63, "sex": 1, "cp": 3, "trestbps": 145,
  "chol": 233, "fbs": 1, "restecg": 0, "thalach": 150,
  "exang": 0, "oldpeak": 2.3, "slope": 0, "ca": 0, "thal": 1
}
```

**Response:**
```json
{
  "prediction": 1,
  "label": "Heart Disease Detected",
  "confidence": 83.0,
  "probability_positive": 83.0,
  "probability_negative": 17.0
}
```

### `POST /api/train`
Retrain the model with custom hyperparameters.

**Request:**
```json
{ "n_estimators": 600, "test_size": 0.2, "random_state": 42 }
```

**Response:**
```json
{
  "accuracy": 83.15,
  "samples_trained": 303,
  "samples_tested": 60,
  "total_samples": 303,
  "feature_importance": { "ca": 0.14, "cp": 0.12, "..." : "..." }
}
```

---

## Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Flask API
python api/predict.py
# → Running on http://localhost:5000

# 3. Open frontend (in a separate terminal)
cd public
python -m http.server 3000
# → Open http://localhost:3000 in browser
```

The pre-trained `.pkl` files are included — prediction works immediately without retraining.

---

## Deploy to Vercel (Frontend Only)

> ⚠️ Vercel serverless functions are stateless — trained `.pkl` files reset on cold start.
> Use Vercel for the **frontend**, and Render/Railway for the **backend**.

### Step 1 — Deploy backend to Render (free)
1. Push this project to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repo
4. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn api.predict:app`
5. Deploy → copy your Render URL (e.g. `https://cardiosense.onrender.com`)

### Step 2 — Update frontend API URL
In `public/index.html`, find line:
```js
const API = '';
```
Change to:
```js
const API = 'https://your-app.onrender.com';
```

### Step 3 — Deploy frontend to Vercel
```bash
npm i -g vercel
vercel
```

---

## Requirements

```
flask==3.0.3
scikit-learn==1.5.0
xgboost==2.0.3
pandas==2.2.2
numpy==1.26.4
joblib==1.4.2
gunicorn==21.2.0
```

---

## Why Not 100% Accuracy?

The model shows 100% on training data — that's **overfitting** (memorizing, not learning).
The honest number is the **10-fold cross-validation score: 83.15%**.

The Cleveland dataset has only 303 samples with natural noise in medical measurements.
Best published results on this dataset top out at ~92–93% with deep feature engineering.

For higher accuracy on real deployments, collect more patient data.
