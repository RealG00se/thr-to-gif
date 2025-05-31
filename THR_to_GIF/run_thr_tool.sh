#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Resolve absolute path using Python (portable, no external deps)
resolve_path() {
  python3 -c "import os,sys; print(os.path.abspath(sys.argv[1]))" "$1"
}

# Default values
ROTATION=0
NO_GIF=""
NO_SVG=""
NO_HTML=""
NO_PNG=""
HTML_TO_GIF=""

# Parse arguments
POSITIONAL=()
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -r|--rotation)
      ROTATION="$2"
      shift # past argument
      shift # past value
      ;;
    --no-gif)
      NO_GIF="--no-gif"
      shift # past argument
      ;;
    --no-svg)
      NO_SVG="--no-svg"
      shift # past argument
      ;;
    --no-html)
      NO_HTML="--no-html"
      shift # past argument
      ;;
    --no-png)
      NO_PNG="--no-png"
      shift # past argument
      ;;
    --html-to-gif)
      HTML_TO_GIF="--html-to-gif"
      shift # past argument
      ;;
    *)
      POSITIONAL+=("$1") # save positional arg
      shift # past argument
      ;;
  esac
done
set -- "${POSITIONAL[@]}"

INPUT="$1"
DURATION="$2"

if [[ -z "$INPUT" || -z "$DURATION" ]]; then
  echo "Usage: $0 file_or_folder duration [-r degrees] [--no-gif] [--no-svg] [--no-html] [--no-png] [--html-to-gif]"
  exit 1
fi

# Use the script directory to find thr_to_gif.py
SCRIPT="$SCRIPT_DIR/thr_to_gif.py"

if [[ -d "$INPUT" ]]; then
  if [[ -n "$HTML_TO_GIF" ]]; then
    echo "📂 Batch processing HTML files in folder: $INPUT"
    # Find all .html files recursively and sort them alphabetically
    find "$INPUT" -type f -name "*.html" | sort | while read -r f; do
      if [[ -f "$f" ]]; then
        full_path=$(resolve_path "$f")
        echo ""
        echo "🔁 Processing HTML: $full_path"
        python3 "$SCRIPT" "$full_path" -d "$DURATION" -r "$ROTATION" $NO_GIF $NO_SVG $NO_HTML $NO_PNG $HTML_TO_GIF
      fi
    done
  else
    echo "📂 Batch processing THR files in folder: $INPUT"
    # Find all .thr files recursively and sort them alphabetically
    find "$INPUT" -type f -name "*.thr" | sort | while read -r f; do
      if [[ -f "$f" ]]; then
        full_path=$(resolve_path "$f")
        echo ""
        echo "🔁 Processing THR: $full_path"
        python3 "$SCRIPT" "$full_path" -d "$DURATION" -r "$ROTATION" $NO_GIF $NO_SVG $NO_HTML $NO_PNG
      fi
    done
  fi
else
  full_path=$(resolve_path "$INPUT")
  if [[ -n "$HTML_TO_GIF" ]]; then
    echo "🎯 Processing single HTML file: $full_path"
  else
    echo "🎯 Processing single THR file: $full_path"
  fi
  python3 "$SCRIPT" "$full_path" -d "$DURATION" -r "$ROTATION" $NO_GIF $NO_SVG $NO_HTML $NO_PNG $HTML_TO_GIF
fi