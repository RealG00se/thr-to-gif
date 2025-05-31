# THR to GIF Converter

This advanced toolchain converts THR (theta, rho) pattern files for kinetic sand tables into animated HTML previews, GIFs, SVGs, and PNG previews. It features intelligent artifact removal, flexible output customization, real-time progress tracking, and high-performance batch processing.

## ✨ Features
- **Smart Conversion**: Converts `.thr` files (polar coordinates) to multiple output formats
- **Artifact Removal**: Automatically removes circle artifacts that cause unwanted lines on sand tables
- **Flexible Output**: Generate any combination of HTML, GIF, SVG, and PNG files
- **Batch Processing**: Recursive directory processing with alphabetical sorting
- **HTML-to-GIF Mode**: Convert existing HTML animations to GIFs
- **Visual Progress**: Real-time progress bars and phase indicators
- **Performance Optimized**: Fast processing with intelligent frame capture optimization
- **Pattern Rotation**: Apply rotation transformations (in degrees)
- **Comprehensive Logging**: Detailed timing and status information

## 🎯 Output Formats
- **HTML**: Interactive animation with playback controls and custom duration settings
- **GIF**: High-quality animated GIF with optimized palette
- **SVG**: Vector graphics for scalable preview
- **PNG**: Static preview image

## 📋 Requirements
- Python 3.7+
- Node.js (for HTML to GIF/PNG capture)
- ffmpeg (for GIF creation)
- Puppeteer (installed automatically via npm)

## 🚀 Installation
1. **Clone the repository** (or copy the files to your project directory)
2. **Install Node.js dependencies**:
   ```sh
   cd gif
   npm install puppeteer canvas
   ```
3. **Install ffmpeg** if not already installed:
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## 💻 Usage

### 1. Batch Processing (Recommended)
Use the shell script for powerful batch processing with full customization:

```sh
./run_thr_tool.sh <file_or_folder> <duration_seconds> [options]
```

**Core Options:**
- `-r <degrees>`: Rotate pattern (default: 0)
- `-s <size>`: SVG canvas size in pixels (default: 1000)

**Output Customization:**
- `--no-gif`: Skip GIF generation (faster processing)
- `--no-png`: Skip PNG preview generation
- `--no-svg`: Skip SVG generation
- `--no-html`: Skip HTML animation generation

**Special Modes:**
- `--html-to-gif`: Process existing HTML files to generate GIFs

**Examples:**
```sh
# Process all THR files in a folder with 10-second animations
./run_thr_tool.sh patterns/ 10

# Fast batch processing - HTML and PNG only (no GIF)
./run_thr_tool.sh patterns/ 10 --no-gif

# Generate only GIFs from existing HTML files
./run_thr_tool.sh patterns/ 10 --html-to-gif --no-png --no-svg --no-html

# Custom rotation and size
./run_thr_tool.sh mypattern.thr 15 -r 90 -s 1500
```

### 2. Direct Python Usage
Run the main Python script directly for single file processing:

```sh
python3 thr_to_gif.py <input_file> [options]
```

**Options:**
- `-d <duration>`: Animation duration in seconds (default: 10)
- `-r <rotation>`: Rotation in degrees (default: 0)
- `-s <size>`: SVG canvas size in pixels (default: 1000)
- `--no-gif`: Skip GIF generation
- `--no-png`: Skip PNG preview generation
- `--no-svg`: Skip SVG generation
- `--no-html`: Skip HTML animation generation
- `--html-to-gif`: Process existing HTML files

**Examples:**
```sh
# Standard conversion with all outputs
python3 thr_to_gif.py pattern.thr -d 8 -r 45

# Fast preview mode (no GIF)
python3 thr_to_gif.py pattern.thr --no-gif

# Convert HTML to GIF only
python3 thr_to_gif.py pattern.html --html-to-gif --no-png
```

## 📁 Output Structure
For each input `.thr` file, the tool creates a subfolder with:
```
pattern_name/
├── pattern_name.thr          # Cleaned THR file (artifact-removed)
├── pattern_name.html         # Interactive HTML animation
├── pattern_name.gif          # Animated GIF
├── pattern_name.png          # PNG preview
└── pattern_name.svg          # SVG vector graphics
```

## 🎬 Real-Time Progress
The tool provides comprehensive visual feedback:

**THR Processing:**
```
🔄 Processing THR file: pattern.thr
🔧 Step 1/5: Processing THR file and removing artifacts...
📊 Step 2/5: Parsing coordinates...
📝 Step 3/5: Generating HTML animation...
🎨 Step 4/5: Generating SVG file...
🎬 Step 5/5: Generating visual outputs...
```

**GIF Generation:**
```
📹 Phase 1/4: Capturing animation frames...
📹 Capturing frames: [████████████████████████████████████████] 100% (300/300)
🔧 Phase 2/4: Processing frames...
🎨 Phase 3/4: Generating color palette...
🌀 Phase 4/4: Creating final GIF...
✅ GIF created successfully in 2.1s
```

## ⚡ Performance Optimization

**Fast Mode (--no-gif):**
- Skips frame capture entirely when only HTML/PNG/SVG needed
- Up to 10x faster for preview-only workflows
- Perfect for batch processing and quick previews

**Smart Frame Capture:**
- Optimized browser reuse for PNG generation
- Intelligent cleanup and immediate exit
- Minimal memory footprint

**Batch Processing:**
- Recursive subdirectory search
- Alphabetical file processing
- Robust error handling continues processing other files

## 🔧 Advanced Features

### HTML-to-GIF Mode
Convert existing HTML animations to GIFs without reprocessing THR files:
```sh
# Convert specific HTML file
./run_thr_tool.sh animation.html 10 --html-to-gif

# Batch convert all HTML files in directory
./run_thr_tool.sh html_folder/ 10 --html-to-gif
```

### Artifact Removal
The tool automatically removes:
- Circle artifacts (duplicate points at 2π)
- Redundant closing points
- Malformed coordinate entries

Only problematic points are removed while preserving pattern continuity.

### Interactive HTML Controls
Generated HTML animations include:
- Play/pause/restart controls
- Scrub bar for manual seeking
- Custom duration input (hours:minutes:seconds)
- Real-time position display

## 🐛 Troubleshooting

**Common Issues:**
- **Missing dependencies:** Ensure `node`, `npm`, and `ffmpeg` are in your PATH
- **Puppeteer installation:** Run `npm install puppeteer` in the gif directory
- **Permission errors:** Ensure write permissions in output directories
- **Large files:** Use `--no-gif` for very long animations to save processing time

**Debug Information:**
- Logs written to `thr_converter.log`
- Detailed timing information for each phase
- Error messages with specific file and line information

## 📊 Performance Benchmarks
Typical processing times (1000x1000px, 10-second animation):
- **HTML + SVG + PNG**: ~1-2 seconds
- **+ GIF (300 frames)**: ~3-5 seconds additional
- **Batch processing**: ~2-4 seconds per file average

## 🛠️ Development
**Main Components:**
- `thr_to_gif.py`: Core conversion engine
- `capture.js`: Browser automation and frame capture
- `run_thr_tool.sh`: Batch processing script
- `artifact_remover.py`: THR file cleaning utilities

**Contributing:**
- Follow existing code style and error handling patterns
- Add comprehensive logging for new features
- Test with various THR file formats and edge cases

## 📄 License
MIT License 