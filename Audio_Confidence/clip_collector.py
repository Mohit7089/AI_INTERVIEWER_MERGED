import pandas as pd
import subprocess
import os
import time
from pydub import AudioSegment
from urllib.parse import urlparse, parse_qs

df = pd.read_excel('ERIC.xlsx', dtype={'START_TIME': str, 'END_TIME': str})[['S.No.', 'LINK', 'START_TIME', 'END_TIME', 'CONFIDENCE']]
df = df.dropna(subset=['LINK'])
df = df[df['LINK'].astype(str).str.startswith('http')]

os.makedirs('dataset/raw', exist_ok=True)
os.makedirs('dataset/clips', exist_ok=True)

# Delete all existing clips so corrupt ones get regenerated
clips_dir = 'dataset/clips'
deleted = 0
for f in os.listdir(clips_dir):
    if f.endswith('.wav'):
        os.remove(os.path.join(clips_dir, f))
        deleted += 1
print(f'Deleted {deleted} existing clips for fresh re-clipping.')

def time_to_ms(t):
    t_str = str(t).strip()
    # handle pandas timedelta string like '1 day, 7:23:00'
    if 'day' in t_str:
        # e.g. '1 day, 7:23:00' means 1*60+7 minutes, 23 seconds
        day_part, time_part = t_str.split(',')
        days = int(day_part.strip().split()[0])
        parts = [int(float(p)) for p in time_part.strip().split(':')]
        total_mins = days * 24 * 60 + parts[0]  # treat as overflow minutes
        # but actually days*24h is too big — just use days as hours→minutes
        return (days * 60 * 60 + parts[0] * 60 + parts[1]) * 1000
    parts = t_str.split(':')
    parts = [int(float(p)) for p in parts]
    if len(parts) == 3:
        # always treat as MM:SS:00 — first value is minutes not hours
        return (parts[0] * 60 + parts[1]) * 1000
    elif len(parts) == 2:
        return (parts[0] * 60 + parts[1]) * 1000

def extract_vid_id(url):
    url = str(url).strip()
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[-1].split('?')[0].split('&')[0]
    elif 'watch?v=' in url:
        return parse_qs(urlparse(url).query).get('v', ['unknown'])[0]
    return 'unknown'

# Download unique videos first
unique_videos = df['LINK'].unique()
video_id_map = {}

for url in unique_videos:
    vid_id = extract_vid_id(url)
    out_path = f'dataset/raw/{vid_id}.wav'
    video_id_map[url] = (vid_id, out_path)

    if not os.path.exists(out_path):
        print(f'Downloading {vid_id}...')
        subprocess.run([
            'yt-dlp',
            '--cookies-from-browser', 'firefox',
            '--no-playlist',
            '-f', '251/140/139',
            '-x', '--audio-format', 'wav',
            '--audio-quality', '0',
            '-o', out_path, url
        ])
        time.sleep(3)

# Clip each entry
for _, row in df.iterrows():
    url = row['LINK']
    vid_id, raw_path = video_id_map[url]
    start_ms = time_to_ms(row['START_TIME'])
    end_ms = time_to_ms(row['END_TIME'])
    label = row['CONFIDENCE'].upper()
    sno = int(row['S.No.'])

    out_clip = f'dataset/clips/{sno:03d}_{vid_id}_{label}.wav'

    if os.path.exists(raw_path) and not os.path.exists(out_clip):
        audio = AudioSegment.from_wav(raw_path)
        clip = audio[start_ms:end_ms]
        if len(clip) < 100:
            print(f'WARNING: clip {sno:03d} is only {len(clip)}ms — check timestamps (start={start_ms}ms, end={end_ms}ms)')
        clip = clip.set_frame_rate(22050).set_channels(1)
        clip.export(out_clip, format='wav')
        print(f'Clipped: {out_clip} ({len(clip)}ms)')
    elif not os.path.exists(raw_path):
        print(f'Skipping clip {sno:03d} — raw file not found: {raw_path}')

print('Done.')