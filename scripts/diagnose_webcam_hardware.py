"""Comprehensive Windows Webcam & Vision Hardware Diagnostic Script."""
import sys
import os
import time
import winreg
import cv2
import numpy as np

def inspect_windows_camera_registry():
    print("--- Windows Camera Privacy Registry Check ---")
    reg_paths = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam\NonPackaged")
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

def test_camera_backends():
    print("\n--- Probing OpenCV VideoCapture Backends & Device Indices ---")
    backends = [
        ("MSMF (Media Foundation)", cv2.CAP_MSMF),
        ("DSHOW (DirectShow)", cv2.CAP_DSHOW),
        ("ANY (Default OpenCV Backend)", cv2.CAP_ANY)
    ]
    
    working_configs = []
    
    for backend_name, backend_id in backends:
        print(f"\nBackend: {backend_name}")
        for idx in range(3):
            t0 = time.perf_counter()
            cap = cv2.VideoCapture(idx, backend_id)
            is_opened = cap.isOpened()
            read_ok = False
            frame_shape = None
            mean_val = 0.0
            
            if is_opened:
                ret, frame = cap.read()
                read_ok = ret and (frame is not None)
                if read_ok:
                    frame_shape = frame.shape
                    mean_val = float(np.mean(frame))
                cap.release()
            else:
                cap.release()
                
            latency_ms = (time.perf_counter() - t0) * 1000
            status_str = "SUCCESS" if read_ok else ("OPENED_NO_FRAME" if is_opened else "FAILED_TO_OPEN")
            print(f"  Device {idx}: [{status_str}] Frame={frame_shape}, Brightness={mean_val:.1f} ({latency_ms:.1f}ms)")
            
            if read_ok:
                working_configs.append((backend_name, backend_id, idx, frame_shape, mean_val))
                
    return working_configs

if __name__ == "__main__":
    inspect_windows_camera_registry()
    working = test_camera_backends()
    print("\n" + "=" * 80)
    print(f"WORKING CAMERA CONFIGURATIONS FOUND: {len(working)}")
    for cfg in working:
        print(f"  -> Backend: {cfg[0]}, Index: {cfg[2]}, Resolution: {cfg[3]}, Mean: {cfg[4]:.1f}")
    print("=" * 80)
