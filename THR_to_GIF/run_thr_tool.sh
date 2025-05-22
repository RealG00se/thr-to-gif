#!/bin/bash

# Resolve absolute path using Python (portable, no external deps)
resolve_path() {
  python3 -c "import os,sys; print(os.path.abspath(sys.argv[1]))" "$1"
}

INPUT="$1"
DURATION="$2"

if [[ -z "$INPUT" || -z "$DURATION" ]]; then
  echo "Usage: $0 file_or_folder duration"
  exit 1
fi

SCRIPT="gif/thr_to_gif.py"

if [[ -d "$INPUT" ]]; then
  echo "📂 Batch processing folder: $INPUT"
  for f in "$INPUT"/*.thr; do
    if [[ -f "$f" ]]; then
      full_path=$(resolve_path "$f")
      echo ""
      echo "🔁 Processing: $full_path"
      python3 "$SCRIPT" "$full_path" -d "$DURATION"
    fi
  done
else
  full_path=$(resolve_path "$INPUT")
  echo "🎯 Processing single file: $full_path"
  python3 "$SCRIPT" "$full_path" -d "$DURATION"
fi