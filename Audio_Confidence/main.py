import io
import os
import numpy as np
import librosa
import joblib
import warnings
warnings.filterwarnings('ignore')

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

# ── Load models ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    model         = joblib.load(os.path.join(BASE_DIR, 'model.pkl'))
    scaler        = joblib.load(os.path.join(BASE_DIR, 'scaler.pkl'))
    label_encoder = joblib.load(os.path.join(BASE_DIR, 'label_encoder.pkl'))
    print('Models loaded successfully')
except Exception as e:
    raise RuntimeError(f'Failed to load model files: {e}')

# ── Constants — must exactly match the training notebook ──────────────────────
SR             = 22050
SEGMENT_LENGTH = 6.0
OVERLAP        = 1.0
N_MFCC         = 13

# ── Response schema ───────────────────────────────────────────────────────────
class ConfidenceResponse(BaseModel):
    question_id       : Optional[str]
    predicted_label   : str
    confidence_score  : float
    probabilities     : dict
    segments_analysed : int
    feature_summary   : dict

# ── Feature extraction — identical to notebook Cell 6 ────────────────────────
def extract_feature(y, sr):
    """Identical to notebook. Returns flat feature list only."""
    duration_sec = len(y) / sr

    f0, voiced_flag, _ = librosa.pyin(y, fmin=75, fmax=300, sr=sr)
    f0_clean = f0[~np.isnan(f0)]
    if len(f0_clean) == 0:
        mean_pitch = pitch_std = pitch_range = 0.0
    else:
        mean_pitch  = np.mean(f0_clean)
        pitch_std   = np.std(f0_clean)
        pitch_range = np.max(f0_clean) - np.min(f0_clean)

    rms = librosa.feature.rms(y=y)[0]
    mean_energy = np.mean(rms)
    energy_std  = np.std(rms)

    intervals = librosa.effects.split(y, top_db=25)
    speech_duration = sum((end - start) for start, end in intervals)
    silence_ratio   = 1 - (speech_duration / len(y))

    pauses   = []
    prev_end = 0
    for start, end in intervals:
        pause_samples = start - prev_end
        if pause_samples > 0:
            pauses.append(pause_samples / sr)
        prev_end = end
    mean_pause_ratio = (np.mean(pauses) / duration_sec) if pauses else 0.0

    onsets      = librosa.onset.onset_detect(y=y, sr=sr)
    speech_rate = len(onsets) / duration_sec

    voiced_ratio = np.sum(voiced_flag) / len(voiced_flag)

    spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    spectral_centroid_mean = np.mean(spec_centroid)
    spectral_centroid_std  = np.std(spec_centroid)

    spec_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    spectral_rolloff_mean = np.mean(spec_rolloff)

    mfccs      = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
    mfcc_means = list(np.mean(mfccs, axis=1))
    mfcc_stds  = list(np.std(mfccs,  axis=1))

    return (
        [mean_pitch, pitch_std, pitch_range,
         mean_energy, energy_std,
         silence_ratio, mean_pause_ratio,
         speech_rate, voiced_ratio,
         spectral_centroid_mean, spectral_centroid_std,
         spectral_rolloff_mean] +
        mfcc_means + mfcc_stds
    )

# ── Segmentation — identical to notebook Cell 8 ───────────────────────────────
def segment_audio(y, sr):
    seg_samples  = int(SEGMENT_LENGTH * sr)
    step_samples = int((SEGMENT_LENGTH - OVERLAP) * sr)
    segments = []
    for start in range(0, len(y) - seg_samples + 1, step_samples):
        segments.append(y[start:start + seg_samples])
    if not segments and len(y) > sr * 2:
        segments.append(y)
    return segments

# ── Inference — identical logic to notebook Cell 30 ──────────────────────────
def predict_confidence(y, sr):
    segments  = segment_audio(y, sr)

    if not segments:
        segments = [y]

    all_proba = []
    for seg in segments:
        feat     = extract_feature(seg, sr)
        x        = np.array(feat).reshape(1, -1)
        x_scaled = scaler.transform(x)
        all_proba.append(model.predict_proba(x_scaled)[0])

    avg_proba = np.mean(all_proba, axis=0)
    prob_map  = dict(zip(label_encoder.classes_, avg_proba))

    confidence_score = (
        1.0 * float(prob_map.get('high',   0)) +
        0.6 * float(prob_map.get('medium', 0)) +
        0.2 * float(prob_map.get('low',    0))
    )

    # feature summary — average the interpretable features across segments
    # extracted separately just for dashboard display, not used in prediction
    seg_feats = [extract_feature(seg, sr) for seg in segments]
    avg_feats = np.mean(seg_feats, axis=0)
    feature_summary = {
        'mean_pitch'      : round(float(avg_feats[0]), 2),
        'pitch_std'       : round(float(avg_feats[1]), 2),
        'mean_energy'     : round(float(avg_feats[3]), 4),
        'energy_std'      : round(float(avg_feats[4]), 4),
        'silence_ratio'   : round(float(avg_feats[5]), 3),
        'mean_pause_ratio': round(float(avg_feats[6]), 4),
        'speech_rate'     : round(float(avg_feats[7]), 2),
        'voiced_ratio'    : round(float(avg_feats[8]), 3),
    }

    return {
        'predicted_label'  : label_encoder.classes_[int(np.argmax(avg_proba))],
        'confidence_score' : round(float(confidence_score), 3),
        'probabilities'    : {k: round(float(v), 3) for k, v in prob_map.items()},
        'segments_analysed': len(segments),
        'feature_summary'  : feature_summary,
    }

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title='Confidence Analysis API',
    description='Analyses interview audio and returns confidence scores',
    version='1.0.0'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get('/ping')
def ping():
    """Health check — Express calls this on startup to verify FastAPI is up."""
    return {'status': 'ok', 'model_loaded': True}


@app.post('/analyse', response_model=ConfidenceResponse)
async def analyse(
    audio      : UploadFile = File(...),
    question_id: Optional[str] = None
):
    """
    Accepts a WAV audio file, returns confidence analysis.

    Express sends:
      - audio: WAV file (convert WebM→WAV in Express before sending)
      - question_id: string to tag the result per question

    Returns:
      - predicted_label   : low / medium / high
      - confidence_score  : 0.0 to 1.0 weighted score
      - probabilities     : per-class probabilities
      - segments_analysed : number of 6s segments analysed
      - feature_summary   : acoustic features for dashboard display
    """
    if not audio.filename.lower().endswith('.wav'):
        raise HTTPException(
            status_code=400,
            detail='Only WAV files accepted. Convert WebM to WAV in Express before sending.'
        )

    try:
        contents = await audio.read()
        y, sr    = librosa.load(io.BytesIO(contents), sr=SR, mono=True)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f'Could not load audio: {e}')

    if len(y) < SR * 2:
        raise HTTPException(
            status_code=422,
            detail='Audio too short — minimum 2 seconds required.'
        )

    try:
        result = predict_confidence(y, sr)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Analysis failed: {e}')

    return ConfidenceResponse(question_id=question_id, **result)


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8007, reload=True)
