import os
import pandas as pd

df = pd.read_excel('ERIC.xlsx')[['S.No.', 'LINK', 'START_TIME', 'END_TIME', 'CONFIDENCE']]
df = df.dropna(subset=['LINK'])
df = df[df['LINK'].astype(str).str.startswith('http')]

clips_dir = 'dataset/clips'
existing = set(os.listdir(clips_dir))

total = len(df)
found = 0
missing = []

for _, row in df.iterrows():
    sno = int(row['S.No.'])
    label = row['CONFIDENCE'].upper()
    # check if any clip file starts with this serial number
    prefix = f'{sno:03d}_'
    match = any(f.startswith(prefix) for f in existing)
    if match:
        found += 1
    else:
        missing.append(sno)

print(f'Total expected : {total}')
print(f'Found          : {found}')
print(f'Missing        : {total - found}')
print()

if missing:
    print('Missing clip numbers:')
    print(missing)

print()
print('Class distribution of found clips:')
found_labels = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
for f in existing:
    for label in ['HIGH', 'MEDIUM', 'LOW']:
        if f.endswith(f'_{label}.wav'):
            found_labels[label] += 1
for k, v in found_labels.items():
    print(f'  {k}: {v}')
