#!/usr/bin/env python3
"""
manifest_editor.py -- Edit AndroidManifest.xml before/after patching
Useful for: adding permissions, changing package name, removing receivers
Usage: python3 manifest_editor.py --apk target.apk --action list-perms
       python3 manifest_editor.py --apk target.apk --action add-perm --perm android.permission.INTERNET
       python3 manifest_editor.py --apk target.apk --action remove-receiver --name com.example.TrackerReceiver
"""
import subprocess, sys, argparse, re, shutil
from pathlib import Path
import xml.etree.ElementTree as ET

def decompile(apk_path):
    """Decompile APK and return working directory"""
    work_dir = Path(f"/tmp/manifest_edit_{Path(apk_path).stem}")
    subprocess.run(f"apktool d {apk_path} -o {work_dir} -f", shell=True, check=True, capture_output=True)
    return work_dir

def recompile(work_dir, out_apk):
    """Recompile APK"""
    subprocess.run(f"apktool b {work_dir} -o {out_apk}", shell=True, check=True, capture_output=True)

def sign_apk(apk_path):
    """Sign with debug key"""
    ks = Path.home() / ".android" / "debug.keystore"
    if not ks.exists():
        print("Generate keystore first: keytool -genkey...")
        return False
    signed = str(apk_path).replace(".apk", "_signed.apk")
    subprocess.run(f"apksigner sign --ks {ks} --ks-pass pass:android --out {signed} {apk_path}",
                   shell=True, check=True, capture_output=True)
    return signed

def list_permissions(work_dir):
    """List all declared permissions"""
    manifest = work_dir / "AndroidManifest.xml"
    content = manifest.read_text()
    perms = re.findall(r'<uses-permission.*?android:name="([^"]+)"', content)
    for p in perms:
        print(f"  {p}")
    return len(perms)

def add_permission(work_dir, perm):
    """Add a permission to the manifest"""
    manifest = work_dir / "AndroidManifest.xml"
    content = manifest.read_text()
    
    # Insert before </manifest>
    perm_line = f'    <uses-permission android:name="{perm}" />\n'
    if perm not in content:
        content = content.replace("</manifest>", perm_line + "</manifest>")
        manifest.write_text(content)
        return True
    return False

def remove_receiver(work_dir, receiver_class):
    """Remove a broadcast receiver"""
    manifest = work_dir / "AndroidManifest.xml"
    content = manifest.read_text()
    
    pattern = f'<receiver.*?android:name="{receiver_class}".*?</receiver>'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, "", content, flags=re.DOTALL)
        manifest.write_text(content)
        return True
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True)
    parser.add_argument("--action", required=True, 
                       choices=["list-perms", "add-perm", "remove-receiver", "extract-manifest"])
    parser.add_argument("--perm", help="Permission name for add-perm")
    parser.add_argument("--name", help="Receiver class name for remove-receiver")
    parser.add_argument("--sign", action="store_true", help="Sign after editing")
    args = parser.parse_args()

    apk = Path(args.apk)
    if not apk.exists():
        print(f"APK not found: {apk}")
        sys.exit(1)

    print(f"\n📝 Manifest Editor — {apk.name}")
    print("=" * 40)

    work_dir = decompile(apk)
    print(f"Decompiled to {work_dir}")

    if args.action == "list-perms":
        count = list_permissions(work_dir)
        print(f"Total permissions: {count}")

    elif args.action == "add-perm":
        if not args.perm:
            print("--perm required")
            sys.exit(1)
        ok = add_permission(work_dir, args.perm)
        print(f"  {'✓ Added' if ok else '✗ Already present'}: {args.perm}")

    elif args.action == "remove-receiver":
        if not args.name:
            print("--name required")
            sys.exit(1)
        ok = remove_receiver(work_dir, args.name)
        print(f"  {'✓ Removed' if ok else '✗ Not found'}: {args.name}")

    elif args.action == "extract-manifest":
        manifest = work_dir / "AndroidManifest.xml"
        out = Path("AndroidManifest.xml")
        shutil.copy(manifest, out)
        print(f"  Extracted to {out}")

    out_apk = Path(f"{apk.stem}_edited.apk")
    recompile(work_dir, out_apk)
    print(f"Recompiled to {out_apk}")

    if args.sign:
        signed = sign_apk(out_apk)
        print(f"Signed: {signed}")
    else:
        print("(Run with --sign to sign the APK)")

    shutil.rmtree(work_dir, ignore_errors=True)
    print("\n✅ Done")

if __name__ == "__main__":
    main()
