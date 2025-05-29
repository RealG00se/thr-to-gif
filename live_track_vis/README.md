# Live Track Visualization

A lightweight HTML-based visualization tool for THR files, optimized for Raspberry Pi Zero 2 W.

## Features

- Interactive HTML animations for THR file visualization
- 480x480 resolution output
- Duration adjustment through UI
- Play/pause and restart controls
- Progress scrubber
- Time display
- Smooth SVG path animations

## Requirements

- Python 3.6+
- numpy
- pandas

## Installation

1. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

```bash
python live_track.py input.thr [duration]
```

Where:
- `input.thr`: Path to the THR file to visualize
- `duration`: (Optional) Animation duration in seconds (default: 10.0)

## Output

The script generates HTML files in the `live_track` directory, with each file representing a 5% increment of the visualization. These files can be viewed in any modern web browser.

## Integration

To integrate with your existing web interface, use the provided HTML/JavaScript code to load the generated HTML files in an iframe instead of static images. 