"""Comprehensive Windows Audio & Microphone Hardware Diagnostic Script."""
import sys
import os
import time
import winreg
import sounddevice as sd
import numpy as np

def inspect_windows_microphone_registry():
    print("--- Windows Microphone Privacy Registry Check ---")
    reg_paths = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone\NonPackaged")
    ]
    
    for root, subkey in reg_paths:
        root_name = "HKCU" if root == winreg.HKEY_CURRENT_USER else "HKLM"
        try:
            with winreg.OpenKey(root, subkey) as key:
                val, _ = winreg.QueryValueEx(key, "Value")
                print(f"[{root_name}] {subkey} -> Value: {val}")
        except FileNotFoundError:
            print(f"[{root_name}] {subkey} -> NOT FOUND")
        except Exception as e:
            print(f"[{root_name}] {subkey} -> Error: {e}")

def enumerate_audio_backends_and_devices():
    print("\n--- Audio Host APIs & Devices ---")
    apis = sd.query_hostapis()
    for idx, api in enumerate(apis):
        print(f"HostAPI {idx}: {api['name']} (Devices: {len(api['devices'])}, Default Input: {api['default_input_device']})")

    devices = sd.query_devices()
    input_devices = []
    print("\nInput Devices:")
    for idx, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            api_name = apis[d['hostapi']]['name']
            input_devices.append((idx, d, api_name))
            print(f"  Device {idx:2d}: [{api_name}] {d['name']} | Channels: {d['max_input_channels']} | SampleRate: {d['default_samplerate']}")
    return input_devices

def test_device_capture(device_idx, api_name, device_name, channels, sr):
    print(f"\nTesting Capture on Device {device_idx} ([{api_name}] {device_name})...")
    duration = 1.0  # 1 second
    try:
        # Try device default sample rate or 16000 or 44100
        sample_rates = [int(sr), 16000, 44100, 48000]
        # Remove duplicates
        sample_rates = list(dict.fromkeys(sample_rates))

        for rate in sample_rates:
            for ch in [1, min(channels, 2)]:
                try:
                    rec = sd.rec(int(duration * rate), samplerate=rate, channels=ch, device=device_idx, dtype='float32')
                    sd.wait()
                    rms = np.sqrt(np.mean(rec**2))
                    peak = np.max(np.abs(rec))
                    print(f"  [SUCCESS] Rate: {rate}Hz, Ch: {ch} | RMS: {rms:.6f}, Peak: {peak:.6f}")
                    return True, rate, ch, rms, peak, rec
                except Exception as inner_e:
                    print(f"  [TRY FAILED] Rate {rate}Hz, Ch {ch}: {inner_e}")
        return False, None, None, None, None, None
    except Exception as e:
        print(f"  [FAILED] Device {device_idx}: {e}")
        return False, None, None, None, None, None

if __name__ == "__main__":
    inspect_windows_microphone_registry()
    inputs = enumerate_audio_backends_and_devices()
    success_count = 0
    for idx, d, api_name in inputs:
        ok, rate, ch, rms, peak, rec = test_device_capture(idx, api_name, d['name'], d['max_input_channels'], d['default_samplerate'])
        if ok:
            success_count += 1
            print(f"  ==> WORKING INPUT DEVICE FOUND: Index {idx} ({d['name']})")

    print(f"\nTotal working input streams: {success_count}/{len(inputs)}")
