"""Fix the CascadeClassifier loading in vision/airtouch/modern_ai_vision.py"""
import os

filepath = os.path.join(os.path.dirname(__file__), 'vision', 'airtouch', 'modern_ai_vision.py')
if not os.path.exists(filepath):
    filepath = r'C:\Users\Ali Raza Zaidi\Desktop\matrix\vision\airtouch\modern_ai_vision.py'

with open(filepath, 'r') as f:
    content = f.read()

# Replace the CascadeClassifier loading with try/except
old_code = """        # Preload common object cascades from OpenCV data
        self.object_cascades = {
            "face": cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml"),
            "eye": cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml"),
            "fullbody": cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_fullbody.xml"),
            "upperbody": cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_upperbody.xml"),
        }"""

new_code = """        # Preload common object cascades from OpenCV data
        self.object_cascades = {}
        cascade_names = [
            "face",
            "eye",
            "fullbody",
            "upperbody"
        ]
        for name in cascade_names:
            try:
                path = cv2.data.haarcascades + f"haarcascade_{name}.xml"
                self.object_cascades[name] = cv2.CascadeClassifier(path)
            except Exception as e:
                logger.warning(f"Failed to load cascade '{name}': {{e}}")
                self.object_cascades[name] = None"""

if old_code in content:
    content = content.replace(old_code, new_code)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"Fixed CascadeClassifier loading in {filepath}")
else:
    print("Could not find the exact code to replace")
    # Show what's actually around that area
    idx = content.find("Preload common")
    if idx >= 0:
        print("Found at position", idx)
        print(content[idx:idx+300])