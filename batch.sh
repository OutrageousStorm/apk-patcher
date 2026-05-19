#!/bin/bash
DIR="${1:-.}"
SSL=0; ROOT=0
[[ "$2" == "--ssl" ]] && SSL=1
[[ "$3" == "--root" ]] && ROOT=1
echo "[Batch APK Patcher]\n"
success=0
for apk in "$DIR"/*.apk; do
    test -f "$apk" || continue
    name=$(basename "$apk" .apk)
    args="--apk $apk"
    ((SSL)) && args="$args --ssl-bypass"
    ((ROOT)) && args="$args --root-bypass"
    python3 patch.py $args >/dev/null 2>&1 && echo "✓ $name" && ((success++)) || echo "✗ $name"
done
echo "\nPatched: $success"
