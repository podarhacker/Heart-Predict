# CardioSense — Heart Disease Prediction Web App

A full-stack web app for heart disease prediction with in-browser model training.

## Project Structure

```
heart-app/
├── api/
│   └── predict.py          # Flask API (all endpoints)
├── public/
│   └── index.html          # Frontend (Predict + Train tabs)
├── heart.csv               # Dataset
├── heart_model.pkl         # Trained model (generated after first train)
├── scaler.pkl              # Scaler (generated after first train)
├── requirements.txt
└── vercel.json             # Vercel deployment config
```

## Features

- **Predict Tab** (default): 13-feature input form → instant prediction with confidence %
- **Train Tab**: Adjust hyperparameters (n_estimators, test split, random seed) → retrain → see accuracy, feature importance, training history

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask server
cd api
python predict.py
# → Server starts at http://localhost:5000

# Open public/index.html in browser
# OR serve it:
cd public && python -m http.server 3000
```

## Deploy to Vercel

### Option 1: Vercel CLI
```bash
npm i -g vercel
cd heart-app
vercel
```

### Option 2: GitHub
1. Push this folder to a GitHub repo
2. Go to vercel.com → New Project → Import repo
3. Vercel auto-detects `vercel.json` and deploys

### After Deploy
- Update the `API` variable in `public/index.html` line ~340:
  ```js
  const API = 'https://your-project.vercel.app';
  ```

## Input Features

| Field | Description |
|-------|-------------|
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
| ca | Number of major vessels (0–3) |
| thal | Thalassemia type (1–3) |

## Notes

- **Vercel limitation**: Vercel's serverless functions are stateless — the trained model is saved to `/tmp` on the server and resets between cold starts. For persistent model storage, connect a cloud storage like AWS S3 or Supabase.
- For persistent training results across sessions, use a database or blob storage (Vercel KV, Supabase, etc.).
