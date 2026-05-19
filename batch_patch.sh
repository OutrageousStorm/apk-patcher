#!/bin/bash
# batch_patch.sh -- Patch multiple APKs in a folder
# Usage: ./batch_patch.sh input_folder [--ssl] [--root] [--sign]
set -e

INPUT_DIR="${1:?Usage: $0 <apk_folder>}"
OUTPUT_DIR="patched_apks_$(date +%Y%m%d_%H%M%S)"
shift

OPTIONS=()
[[ " $@ " =~ " --ssl " ]] && OPTIONS+=(--ssl-bypass)
[[ " $@ " =~ " --root " ]] && OPTIONS+=(--root-bypass)
[[ " $@ " =~ " --sign " ]] && OPTIONS+=(--sign)

[[ ! -d "$INPUT_DIR" ]] && echo "❌ Directory not found: $INPUT_DIR" && exit 1

mkdir -p "$OUTPUT_DIR"
echo "🩹 Batch APK Patcher"
echo "Input:  $INPUT_DIR"
echo "Output: $OUTPUT_DIR"
echo "Options: ${OPTIONS[@]:-none}"
echo ""

success=0; fail=0
for apk in "$INPUT_DIR"/*.apk; do
    [[ -f "$apk" ]] || continue
    name=$(basename "$apk" .apk)
    echo "Patching: $name..."
    
    if python3 patch.py --apk "$apk" "${OPTIONS[@]}" --output "$OUTPUT_DIR/${name}_patched.apk" 2>/dev/null; then
        echo "  ✅ $name"
        ((success++))
    else
        echo "  ❌ $name"
        ((fail++))
    fi
done

echo ""
echo "Result: ${success}✅  ${fail}❌"
echo "Output: $(realpath $OUTPUT_DIR)"
