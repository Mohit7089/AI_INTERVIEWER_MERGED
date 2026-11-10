# Interview Confidence Classifier

A machine learning pipeline that analyses interview audio recordings and classifies candidate confidence as **Low**, **Medium**, or **High** — with a weighted confidence score and acoustic feature breakdown for dashboard visualization.

Built as part of an AI-Powered Mock Interview Platform.

---

## What It Does

When a candidate answers an interview question, the system:

1. Receives the audio recording of their answer
2. Segments it into 6-second overlapping windows
3. Extracts 38 acoustic features per segment — pitch, energy, silence patterns, MFCCs, and spectral features
4. Runs each segment through a trained SVM classifier
5. Averages probabilities across all segments
6. Returns a confidence label, a weighted confidence score (0–1), and a feature summary for the dashboard

---

## Model Performance

| Class | Precision | Recall | F1 |
|-------|-----------|--------|----|
| High | 0.84 | 0.78 | 0.81 |
| Low | 0.73 | 0.74 | 0.74 |
| Medium | 0.62 | 0.67 | 0.64 |
| **Overall** | | | **0.73** |

- Model: SVM with polynomial kernel (C=10, gamma='auto')
- Training data: 660 segments from 135 labeled YouTube interview clips
- Cross-validation accuracy: 76.5%

---

## Dataset

The dataset was built from scratch by manually collecting and labeling real interview audio from YouTube.

### Collection Process
- Identified 40 YouTube videos of mock interviews across various roles
- Manually noted timestamps of individual answers and labeled each as LOW / MEDIUM / HIGH confidence
- Labels are based on acoustic confidence signals — speech rate, hesitation, vocal steadiness, articulation — not answer quality
- All metadata is documented in `Dataset.xlsx`

### Dataset Stats
- 135 labeled audio clips across 40 YouTube videos
- Class distribution: HIGH: 46, MEDIUM: 42, LOW: 47
- After 6s segmentation with 1s overlap: 660 training segments

### Reproducing the Dataset
1. Install dependencies: `pip install -r requirements.txt yt-dlp pydub`
2. Run `clip_collector.py` — downloads audio from YouTube URLs in `Dataset.xlsx` and clips each entry by timestamp
3. Run the feature extraction section of `confidence_classifier.ipynb` to generate `dataset/features.csv`

> Note: Some YouTube videos may no longer be available. The `Dataset.xlsx` file preserves all source URLs, timestamps, and labels for reference.

---

## Features Extracted

**Pitch (3)** — mean pitch, pitch standard deviation, pitch range. Captures vocal expressiveness and stability.

**Energy (2)** — mean RMS energy, energy standard deviation. Energy std was the 2nd most important feature — confident speakers maintain steadier loudness.

**Silence & Pauses (2)** — silence ratio, mean pause ratio. Hesitant speakers have longer and more frequent pauses.

**Speech Rate (1)** — onset density (syllable-like events per second).

**Voiced Ratio (1)** — fraction of frames containing voiced speech.

**Spectral (3)** — spectral centroid mean/std, spectral rolloff mean. Captures voice brightness and articulation clarity.

**MFCCs (26)** — mean and standard deviation of 13 Mel-Frequency Cepstral Coefficients. The most important feature group — particularly mfcc_8_mean, mfcc_12_mean, and the std values of coefficients 7–10 which capture articulation consistency.

---

## Project Structure

```
confidence/
├── main.py                      # FastAPI app — /analyse endpoint
├── confidence_classifier.ipynb  # Full pipeline — feature extraction + training
├── clip_collector.py            # Downloads and clips YouTube audio
├── audit_clips.py               # Checks clip counts and class distribution
├── Dataset.xlsx                 # Labeled dataset — YouTube URLs + timestamps + labels
├── requirements.txt             # Python dependencies
├── model.pkl                    # Trained SVM model
├── scaler.pkl                   # StandardScaler fitted on training data
└── label_encoder.pkl            # LabelEncoder for LOW / MEDIUM / HIGH classes
```

---

## API

The FastAPI app exposes a single endpoint that the Express backend calls after receiving a candidate's answer audio.

### Start the server

```bash
pip install -r requirements.txt
python main.py
```

Server runs at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Endpoints

**GET /ping** — health check

```json
{ "status": "ok", "model_loaded": true }
```

**POST /analyse** — analyse an audio file

| Field | Type | Description |
|-------|------|-------------|
| audio | file | WAV file (convert WebM → WAV before sending) |
| question_id | string (optional) | tags the result per question |

Example response:

```json
{
  "question_id": "q3",
  "predicted_label": "medium",
  "confidence_score": 0.623,
  "probabilities": {
    "high": 0.31,
    "medium": 0.52,
    "low": 0.17
  },
  "segments_analysed": 4,
  "feature_summary": {
    "mean_pitch": 187.4,
    "pitch_std": 22.1,
    "mean_energy": 0.061,
    "energy_std": 0.038,
    "silence_ratio": 0.21,
    "speech_rate": 4.3,
    "voiced_ratio": 0.74,
    "mean_pause_ratio": 0.031
  }
}
```

The `confidence_score` is computed as:
```
score = 1.0 × P(high) + 0.6 × P(medium) + 0.2 × P(low)
```

---

## How Express Calls This

```javascript
const FormData = require('form-data')
const fetch    = require('node-fetch')
const fs       = require('fs')

// audio must be converted from WebM to WAV first using ffmpeg
const form = new FormData()
form.append('audio', fs.createReadStream('answer.wav'))
form.append('question_id', 'q3')

const response = await fetch('http://localhost:8000/analyse', {
    method: 'POST',
    body  : form,
    headers: form.getHeaders()
})

const result = await response.json()
// store result in MongoDB, return to React for dashboard
```

---

## Reproducing the Model

1. Collect and clip audio using `clip_collector.py` (requires `Dataset.xlsx`)
2. Open `confidence_classifier.ipynb`
3. Run all cells — feature extraction takes ~15 minutes due to pitch detection
4. Model, scaler, and label encoder are saved as `.pkl` files automatically

---

## Tech Stack

- **Python** — librosa, scikit-learn, FastAPI, joblib
- **Model** — SVM (sklearn.svm.SVC) with polynomial kernel
- **Audio processing** — librosa for feature extraction, pydub for clipping
- **Data collection** — yt-dlp for YouTube audio download
- **API** — FastAPI + uvicorn
- **Labeling tool** — manual labeling with Label Studio

---

## Part of

This confidence classifier is one component of the **AI-Powered Mock Interview Platform** — a full-stack web application where candidates practice interviews with an AI interviewer. The platform also includes resume parsing, adaptive LLM-based questioning, real-time TTS/STT, and video-based eye contact and posture analysis.