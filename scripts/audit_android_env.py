import shutil
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=== ANDROID TOOLCHAIN & ENVIRONMENT AUDIT ===")
tools = ['java', 'javac', 'gradle', 'gradlew', 'adb']
for t in tools:
    path = shutil.which(t)
    print(f"  {t:<10} : {'FOUND -> ' + path if path else 'NOT FOUND in PATH'}")

for var in ['ANDROID_HOME', 'ANDROID_SDK_ROOT', 'JAVA_HOME']:
    val = os.getenv(var)
    print(f"  {var:<16} : {val if val else 'NOT SET'}")

# Also check common default paths for Android SDK and Java on Windows
common_android = [
    os.path.expanduser("~/AppData/Local/Android/Sdk"),
    "C:/Program Files/Android/Android Studio",
    "C:/Android/Sdk"
]
print("\nChecking common Android paths:")
for p in common_android:
    print(f"  {p} : {'EXISTS' if os.path.exists(p) else 'DOES NOT EXIST'}")

common_java = [
    "C:/Program Files/Java",
    "C:/Program Files/Eclipse Adoptium",
    "C:/Program Files/Android/Android Studio/jbr"
]
print("\nChecking common Java paths:")
for p in common_java:
    print(f"  {p} : {'EXISTS' if os.path.exists(p) else 'DOES NOT EXIST'}")
