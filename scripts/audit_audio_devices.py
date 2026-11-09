"""Audio device diagnostic script."""
import sounddevice as sd
import json

print("=== AUDIO INPUT DEVICES ENUMERATION ===")
default_in = sd.default.device[0]
print(f"Default input device index: {default_in}")

devices = sd.query_devices()
input_devices = []
for i, d in enumerate(devices):
    if d['max_input_channels'] > 0:
        hostapi_name = sd.query_hostapis(d['hostapi'])['name']
        is_def = (i == default_in)
        info = {
            "index": i,
            "name": d['name'],
            "hostapi": hostapi_name,
            "max_input_channels": d['max_input_channels'],
            "default_samplerate": d['default_samplerate'],
            "is_default": is_def
        }
        input_devices.append(info)
        print(f"[{i:2}] {d['name'][:40]:40} | Host: {hostapi_name:15} | Ch: {d['max_input_channels']} | Rate: {d['default_samplerate']} {'(DEFAULT)' if is_def else ''}")

print(f"\nTotal input devices: {len(input_devices)}")
