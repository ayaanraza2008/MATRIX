import zipfile

apk_path = r"C:\Users\Ali Raza Zaidi\Desktop\matrix\mobile\android_app\app\build\outputs\apk\debug\app-debug.apk"
with zipfile.ZipFile(apk_path, 'r') as zf:
    # Find AndroidManifest.xml
    manifest_entry = None
    for entry in zf.namelist():
        if entry.endswith('AndroidManifest.xml'):
            manifest_entry = entry
            break

    if manifest_entry:
        manifest = zf.read(manifest_entry).decode('utf-8', errors='ignore')
        # Print first 800 chars for analysis
        print(manifest[:800])
    else:
        print('AndroidManifest.xml not found')