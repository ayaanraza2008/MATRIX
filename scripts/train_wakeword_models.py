"""MATRIX Wake-Word Model Generator & Trainer (Hard-Negative Mined).
Generates synthetic speech samples for 'Matrix', 'Snap', and targeted phonemic foils,
extracts openWakeWord embeddings, trains lightweight ONNX neural classifiers,
and exports them to D:\matrix_data\models\wakeword.
"""
import os
import sys
import time
import asyncio
import subprocess
import shutil
from pathlib import Path
import numpy as np
import scipy.io.wavfile as wavfile
import torch
import torch.nn as nn
from openwakeword.utils import AudioFeatures
import openwakeword
from openwakeword.model import Model

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

OUTPUT_DIR = Path(r"D:\matrix_data\models\wakeword")
SAMPLE_CACHE_DIR = Path(r"D:\matrix_data\models\wakeword\samples")

VOICES = [
    "en-US-ChristopherNeural",
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    "en-GB-RyanNeural",
    "en-GB-SoniaNeural",
    "en-IN-PrabhatNeural",
    "en-IN-NeerjaNeural",
    "en-AU-WilliamNeural"
]

RATES = ["-15%", "+0%", "+15%"]

MATRIX_PHRASES = ["Matrix", "Hey Matrix", "Matrix please", "Okay Matrix"]
SNAP_PHRASES = ["Snap", "Hey Snap", "Snap now"]

# Targeted hard negatives for Snap & Matrix
HARD_NEGATIVES_SNAP = [
    "Jarvis", "Hey Jarvis", "Computer", "Hello computer", "Stop", "Wait",
    "Start", "Tap", "Step", "Skip", "Sleep", "Drop", "Desktop", "Help",
    "Map", "App", "Cap", "Trap", "Clap", "Slap", "Black", "Track"
]

HARD_NEGATIVES_MATRIX = [
    "Metric", "Magic", "Music", "Master", "Notice", "Matter",
    "Mix", "Fix", "Match", "Max", "Status", "Lattice"
]

GENERAL_NEGATIVES = [
    "Alexa", "Siri", "Google", "Hey Google", "Hello", "Cancel", "Play", "Pause",
    "What time is it", "Search the web", "Summarize this file", "Open settings",
    "Python", "System memory", "Show agents", "Turn on lights", "Good evening",
    "Namaste", "Theek hai", "Shukriya", "Batao", "Kaam karo", "Kaise ho"
]


class WakeWordNet(nn.Module):
    """Compact wake-word classifier mapping 16x96 audio embeddings to detection probability."""
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(16 * 96, 64),
            nn.LayerNorm(64),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(64, 32),
            nn.LayerNorm(32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.net(x)


async def synthesize_clip_cached(text: str, voice: str, rate: str, out_wav: Path):
    """Synthesize speech using edge-tts and convert to 16kHz mono WAV via ffmpeg with caching."""
    if out_wav.exists() and out_wav.stat().st_size > 500:
        return True

    import edge_tts
    temp_mp3 = out_wav.with_suffix(".mp3")
    try:
        comm = edge_tts.Communicate(text, voice, rate=rate)
        await comm.save(str(temp_mp3))
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(temp_mp3),
            "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
            "-af", "apad=pad_dur=0.5",
            str(out_wav)
        ]
        subprocess.run(cmd, check=True)
        if temp_mp3.exists():
            temp_mp3.unlink()
        return out_wav.exists() and out_wav.stat().st_size > 500
    except Exception as e:
        if temp_mp3.exists():
            temp_mp3.unlink()
        return False


def extract_features_from_wav(wav_path: Path, af: AudioFeatures) -> list:
    """Extract (16, 96) embedding windows from a 16kHz WAV file."""
    try:
        sr, data = wavfile.read(str(wav_path))
        if data.ndim > 1:
            data = data[:, 0]
        if data.dtype != np.int16:
            data = (data * 32767).astype(np.int16)

        if len(data) < 24000:
            pad_before = np.zeros(4000, dtype=np.int16)
            pad_after = np.zeros(24000 - len(data) - 4000 if len(data) < 20000 else 4000, dtype=np.int16)
            data = np.concatenate([pad_before, data, pad_after])

        af.reset()
        features_list = []
        for i in range(0, len(data) - 1280, 1280):
            chunk = data[i:i + 1280]
            af(chunk)
            feats = af.get_features(16)
            if feats is not None and feats.shape == (1, 16, 96):
                features_list.append(feats[0])

        return features_list
    except Exception as e:
        return []


async def generate_dataset():
    """Synthesize dataset with caching and extract embeddings."""
    SAMPLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    af = AudioFeatures()

    matrix_features = []
    snap_features = []
    hard_neg_snap_features = []
    hard_neg_matrix_features = []
    general_neg_features = []

    print("[*] Loading / generating audio samples via edge-tts with disk caching...")

    # 1. MATRIX samples
    clip_id = 0
    for phrase in MATRIX_PHRASES:
        for voice in VOICES:
            for rate in RATES[:2]:
                wav_file = SAMPLE_CACHE_DIR / f"matrix_{clip_id}.wav"
                clip_id += 1
                ok = await synthesize_clip_cached(phrase, voice, rate, wav_file)
                if ok:
                    feats = extract_features_from_wav(wav_file, af)
                    if feats:
                        matrix_features.extend(feats[max(0, len(feats) - 6):])

    print(f"[+] Extracted {len(matrix_features)} feature windows for 'Matrix'.")

    # 2. SNAP samples
    clip_id = 0
    for phrase in SNAP_PHRASES:
        for voice in VOICES:
            for rate in RATES:
                wav_file = SAMPLE_CACHE_DIR / f"snap_{clip_id}.wav"
                clip_id += 1
                ok = await synthesize_clip_cached(phrase, voice, rate, wav_file)
                if ok:
                    feats = extract_features_from_wav(wav_file, af)
                    if feats:
                        snap_features.extend(feats[max(0, len(feats) - 5):])

    print(f"[+] Extracted {len(snap_features)} feature windows for 'Snap'.")

    # 3. Hard Negatives for Snap
    clip_id = 0
    for phrase in HARD_NEGATIVES_SNAP:
        for voice in VOICES[:4]:
            wav_file = SAMPLE_CACHE_DIR / f"hard_snap_{clip_id}.wav"
            clip_id += 1
            ok = await synthesize_clip_cached(phrase, voice, "+0%", wav_file)
            if ok:
                feats = extract_features_from_wav(wav_file, af)
                if feats:
                    hard_neg_snap_features.extend(feats)

    print(f"[+] Extracted {len(hard_neg_snap_features)} feature windows for Hard Negatives (Snap).")

    # 4. Hard Negatives for Matrix
    clip_id = 0
    for phrase in HARD_NEGATIVES_MATRIX:
        for voice in VOICES[:4]:
            wav_file = SAMPLE_CACHE_DIR / f"hard_matrix_{clip_id}.wav"
            clip_id += 1
            ok = await synthesize_clip_cached(phrase, voice, "+0%", wav_file)
            if ok:
                feats = extract_features_from_wav(wav_file, af)
                if feats:
                    hard_neg_matrix_features.extend(feats)

    # 5. General Negatives
    clip_id = 0
    for phrase in GENERAL_NEGATIVES:
        voice = VOICES[clip_id % len(VOICES)]
        wav_file = SAMPLE_CACHE_DIR / f"gen_neg_{clip_id}.wav"
        clip_id += 1
        ok = await synthesize_clip_cached(phrase, voice, "+0%", wav_file)
        if ok:
            feats = extract_features_from_wav(wav_file, af)
            if feats:
                general_neg_features.extend(feats)

    # Add pure silence and ambient noise samples as negatives
    for _ in range(25):
        noise = (np.random.randn(24000) * 120).astype(np.int16)
        wav_file = SAMPLE_CACHE_DIR / "noise_sample.wav"
        wavfile.write(str(wav_file), 16000, noise)
        feats = extract_features_from_wav(wav_file, af)
        general_neg_features.extend(feats)
        if wav_file.exists():
            wav_file.unlink()

    print(f"[+] Extracted {len(general_neg_features)} feature windows for General Negatives.")

    return {
        "matrix": np.array(matrix_features, dtype=np.float32),
        "snap": np.array(snap_features, dtype=np.float32),
        "hard_snap": np.array(hard_neg_snap_features, dtype=np.float32),
        "hard_matrix": np.array(hard_neg_matrix_features, dtype=np.float32),
        "general_neg": np.array(general_neg_features, dtype=np.float32)
    }


def train_and_export_model(
    pos_data: np.ndarray,
    neg_data: np.ndarray,
    target_name: str,
    output_onnx: Path
):
    """Train PyTorch model with weighted negative penalty and export to ONNX."""
    print(f"\n[*] Training classifier for '{target_name}'...")
    print(f"    Positive samples: {len(pos_data)}, Negative samples: {len(neg_data)}")

    # Jitter augmentation
    pos_aug = []
    for p in pos_data:
        pos_aug.append(p)
        pos_aug.append(p + np.random.normal(0, 0.02, p.shape).astype(np.float32))
        pos_aug.append(p + np.random.normal(0, 0.03, p.shape).astype(np.float32))
    pos_arr = np.array(pos_aug, dtype=np.float32)

    X = np.concatenate([pos_arr, neg_data], axis=0)
    y = np.concatenate([
        np.ones(len(pos_arr), dtype=np.float32),
        np.zeros(len(neg_data), dtype=np.float32)
    ], axis=0)

    # Weights: penalize false positives 2.5x more heavily than false negatives
    sample_weights = np.concatenate([
        np.ones(len(pos_arr), dtype=np.float32),
        np.full(len(neg_data), 2.5, dtype=np.float32)
    ], axis=0)

    indices = np.random.permutation(len(X))
    X = torch.tensor(X[indices])
    y = torch.tensor(y[indices]).unsqueeze(1)
    sw = torch.tensor(sample_weights[indices]).unsqueeze(1)

    model = WakeWordNet()
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.002, weight_decay=1e-4)

    batch_size = 32
    epochs = 40
    dataset = torch.utils.data.TensorDataset(X, y, sw)
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    for epoch in range(epochs):
        epoch_loss = 0.0
        for bx, by, bw in loader:
            optimizer.zero_grad()
            out = model(bx)
            # Weighted binary cross entropy
            loss = torch.nn.functional.binary_cross_entropy(out, by, weight=bw)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * len(bx)
        if (epoch + 1) % 10 == 0:
            print(f"    Epoch {epoch + 1}/{epochs} - Loss: {epoch_loss / len(X):.4f}")

    # Evaluate
    model.eval()
    with torch.no_grad():
        preds = (model(X) >= 0.5).float()
        acc = (preds == y).float().mean().item()
        print(f"[+] Final Training Accuracy for '{target_name}': {acc * 100:.2f}%")

    output_onnx.parent.mkdir(parents=True, exist_ok=True)
    dummy_input = torch.randn(1, 16, 96, dtype=torch.float32)
    torch.onnx.export(
        model,
        dummy_input,
        str(output_onnx),
        input_names=["x.1"],
        output_names=["output"],
        dynamic_axes={"x.1": {0: "batch"}, "output": {0: "batch"}},
        dynamo=False
    )
    print(f"[+] Successfully exported ONNX model to: {output_onnx} ({output_onnx.stat().st_size} bytes)")


async def main():
    print("=" * 70)
    print(" MATRIX WAKE-WORD MODEL TRAINER (Hard-Negative Mined ONNX)")
    print("=" * 70)

    data = await generate_dataset()

    # For MATRIX: negatives include general negatives + hard matrix + snap positives
    matrix_neg = np.concatenate([
        data["general_neg"],
        data["hard_matrix"],
        data["snap"]
    ], axis=0)

    train_and_export_model(
        data["matrix"],
        matrix_neg,
        "matrix",
        OUTPUT_DIR / "matrix.onnx"
    )

    # For SNAP: negatives include general negatives + hard snap (Jarvis, computer, etc.) + matrix positives
    snap_neg = np.concatenate([
        data["general_neg"],
        data["hard_snap"],
        data["hard_snap"],  # 2x weight on hard plosive negatives
        data["matrix"]
    ], axis=0)

    train_and_export_model(
        data["snap"],
        snap_neg,
        "snap",
        OUTPUT_DIR / "snap.onnx"
    )

    print("\n[*] Verifying openWakeWord integration with newly trained models...")
    oww = Model(
        wakeword_models=[
            str(OUTPUT_DIR / "matrix.onnx"),
            str(OUTPUT_DIR / "snap.onnx")
        ],
        inference_framework="onnx"
    )
    print(f"[+] Loaded models in openWakeWord: {list(oww.models.keys())}")
    test_chunk = np.random.randint(-500, 500, 1280, dtype=np.int16)
    pred = oww.predict(test_chunk)
    print(f"[+] Baseline prediction on noise: {pred}")
    print("\n[✔] RETRAINING COMPLETED!\n")


if __name__ == "__main__":
    asyncio.run(main())
