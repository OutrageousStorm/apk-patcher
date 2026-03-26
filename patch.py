#!/usr/bin/env python3
"""
patch.py -- Patch Android APKs for security research
Supports: SSL pinning bypass, root detection bypass, network security config injection
Usage: python3 patch.py --apk target.apk --ssl-bypass --root-bypass --sign
"""
import subprocess, sys, os, shutil, argparse, re
from pathlib import Path

def run(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and r.returncode != 0:
        print(f"  ERROR: {cmd}")
        print(r.stderr[:300])
        sys.exit(1)
    return r.stdout + r.stderr

def check_deps():
    missing = [t for t in ["apktool", "java"] if not shutil.which(t)]
    if missing:
        print(f"Missing tools: {', '.join(missing)}")
        print("Install apktool: https://apktool.org")
        sys.exit(1)

def decompile(apk_path, out_dir):
    print(f"  Decompiling {apk_path.name}...")
    run(f'apktool d "{apk_path}" -o "{out_dir}" -f')
    print("  OK: Decompiled")

def recompile(work_dir, out_apk):
    print("  Recompiling...")
    run(f'apktool b "{work_dir}" -o "{out_apk}"')
    print("  OK: Recompiled")

def sign_apk(apk_path):
    ks = Path.home() / ".android" / "debug.keystore"
    if not ks.exists():
        print("  Generating debug keystore...")
        run(
            f'keytool -genkeypair -v -keystore "{ks}" -storepass android '
            f'-alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 '
            f'-validity 10000 -dname "CN=Android Debug,O=Android,C=US"'
        )
    signed = str(apk_path).replace(".apk", "_signed.apk")
    if shutil.which("zipalign"):
        aligned = str(apk_path).replace(".apk", "_aligned.apk")
        run(f'zipalign -f 4 "{apk_path}" "{aligned}"')
        apk_path = Path(aligned)
    if shutil.which("apksigner"):
        run(
            f'apksigner sign --ks "{ks}" --ks-pass pass:android '
            f'--key-pass pass:android --out "{signed}" "{apk_path}"'
        )
    else:
        run(
            f'jarsigner -keystore "{ks}" -storepass android '
            f'-keypass android -signedjar "{signed}" "{apk_path}" androiddebugkey'
        )
    print(f"  OK: Signed -> {signed}")
    return signed

NSC_XML = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<network-security-config>\n'
    '    <base-config cleartextTrafficPermitted="true">\n'
    '        <trust-anchors>\n'
    '            <certificates src="system"/>\n'
    '            <certificates src="user"/>\n'
    '        </trust-anchors>\n'
    '    </base-config>\n'
    '</network-security-config>\n'
)

def patch_ssl_bypass(work_dir):
    print("  Patching SSL pinning...")
    res_dir = work_dir / "res" / "xml"
    res_dir.mkdir(parents=True, exist_ok=True)
    (res_dir / "network_security_config.xml").write_text(NSC_XML)

    manifest = work_dir / "AndroidManifest.xml"
    content = manifest.read_text()
    if "networkSecurityConfig" not in content:
        content = content.replace(
            "android:allowBackup=",
            'android:networkSecurityConfig="@xml/network_security_config"\n        android:allowBackup='
        )
        manifest.write_text(content)

    patched_smali = 0
    for smali in work_dir.rglob("*.smali"):
        text = smali.read_text()
        if "Lokhttp3/CertificatePinner;->check" in text:
            new_text = re.sub(
                r'(invoke-virtual \{[^}]+\}, Lokhttp3/CertificatePinner;->check[^\n]+)',
                r'# SSL bypass: \1\n    return-void',
                text
            )
            if new_text != text:
                smali.write_text(new_text)
                patched_smali += 1
    print(f"  OK: SSL bypass (NSC + {patched_smali} Smali patches)")

def patch_root_bypass(work_dir):
    print("  Patching root detection...")
    root_methods = ["isRooted", "checkRoot", "detectRoot", "isDeviceRooted", "isRootAvailable"]
    su_paths = ["/system/xbin/su", "/sbin/su", "/system/bin/su", "/data/local/tmp/su"]
    patched = 0
    for smali in work_dir.rglob("*.smali"):
        text = smali.read_text()
        changed = False
        for method in root_methods:
            pattern = rf'(\.method public (?:static )?{method}\(\)Z)'
            if re.search(pattern, text):
                def inject_return(m):
                    return m.group(1) + "\n    const/4 v0, 0x0\n    return v0"
                new_text = re.sub(pattern, inject_return, text, count=1)
                if new_text != text:
                    text = new_text
                    changed = True
                    patched += 1
        for path in su_paths:
            fake = "/__patched_su_nonexistent__"
            if path in text:
                text = text.replace(f'"{path}"', f'"{fake}"')
                changed = True
                patched += 1
        if changed:
            smali.write_text(text)
    print(f"  OK: Root bypass ({patched} patches)")

def main():
    parser = argparse.ArgumentParser(description="Patch Android APKs for security research")
    parser.add_argument("--apk", required=True)
    parser.add_argument("--ssl-bypass", action="store_true")
    parser.add_argument("--root-bypass", action="store_true")
    parser.add_argument("--sign", action="store_true")
    parser.add_argument("--output", help="Output APK path")
    args = parser.parse_args()

    check_deps()
    apk = Path(args.apk)
    if not apk.exists():
        print(f"APK not found: {apk}"); sys.exit(1)

    work_dir = Path(f"/tmp/apk_patch_{apk.stem}")
    out_apk = Path(args.output or f"{apk.stem}_patched.apk")

    print(f"\nAPK Patcher -- {apk.name}")
    print("=" * 40)
    decompile(apk, work_dir)

    if args.ssl_bypass:
        patch_ssl_bypass(work_dir)
    if args.root_bypass:
        patch_root_bypass(work_dir)
    if not args.ssl_bypass and not args.root_bypass:
        print("No patches selected. Use --ssl-bypass and/or --root-bypass")
        sys.exit(0)

    recompile(work_dir, out_apk)
    if args.sign:
        out_apk = sign_apk(out_apk)

    shutil.rmtree(work_dir, ignore_errors=True)
    print(f"\nDone -> {out_apk}")
    print(f"Install: adb install {out_apk}")

if __name__ == "__main__":
    main()
