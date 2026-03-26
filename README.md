# APK Patcher

Patch Android APKs — SSL pinning bypass, root detection bypass.

## Requirements
```bash
# apktool in PATH: https://apktool.org
# java in PATH
```

## Usage
```bash
# Disable SSL pinning
python3 patch.py --apk target.apk --ssl-bypass

# Bypass root detection
python3 patch.py --apk target.apk --root-bypass

# Both + sign
python3 patch.py --apk target.apk --ssl-bypass --root-bypass --sign
```

## What it does
- **SSL bypass**: injects `network_security_config.xml` trusting user CAs + patches OkHttp Smali
- **Root bypass**: patches `isRooted()`/`checkRoot()` methods to return false, replaces su path strings
- **Sign**: auto-generates debug keystore, zipaligns and signs with `apksigner`

*Educational use only.*
