#!/usr/bin/env python3
import os
import sys
import math
import numpy as np
import pandas as pd
from typing import List, Tuple

# Configuration
INPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else 'data.thr'
OUT_DIR = 'live_track'
SVG_SIZE = 480  # 480x480 pixels as requested
OFFSET = 1.57079  # angle offset

def polar_to_cartesian(r: float, theta: float) -> Tuple[float, float]:
    """Convert polar coordinates to cartesian coordinates."""
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return x, y

def generate_svg_path(coords: List[Tuple[float, float]], svg_size: int) -> Tuple[str, List[Tuple[float, float]]]:
    """Generate SVG path data from coordinates and scale to fit SVG size."""
    if not coords:
        return "", []
    
    # Find bounds
    min_x = min(x for x, _ in coords)
    max_x = max(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    max_y = max(y for _, y in coords)
    
    # Calculate scale to fit SVG size with padding
    padding = svg_size * 0.1
    scale = min(
        (svg_size - 2 * padding) / (max_x - min_x) if max_x != min_x else 1,
        (svg_size - 2 * padding) / (max_y - min_y) if max_y != min_y else 1
    )
    
    # Center the path
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    
    # Scale and translate points
    scaled_points = []
    for x, y in coords:
        # Center and scale
        centered_x = (x - center_x) * scale
        centered_y = (y - center_y) * scale
        # Rotate 90 degrees counterclockwise
        rotated_x = centered_y
        rotated_y = -centered_x
        # Translate to center of SVG
        final_x = rotated_x + svg_size / 2
        final_y = rotated_y + svg_size / 2
        scaled_points.append((final_x, final_y))
    
    # Generate path data
    if not scaled_points:
        return "", []
    
    path_data = f"M {scaled_points[0][0]:.2f} {scaled_points[0][1]:.2f}"
    for x, y in scaled_points[1:]:
        path_data += f" L {x:.2f} {y:.2f}"
    
    return path_data, scaled_points

def calculate_path_length(points: List[Tuple[float, float]]) -> float:
    """Calculate the total length of the path."""
    if len(points) < 2:
        return 0
    
    total_length = 0
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        total_length += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    return total_length

def generate_html(path_data: str, path_length: float, duration: float, svg_size: int) -> str:
    """Generate HTML with SVG animation."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Live Track Animation</title>
  <style>
    body {{
      margin: 0;
      background-color: black;
      color: white;
      font-family: sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
    }}
    svg {{
      width: {svg_size}px;
      height: {svg_size}px;
    }}
    .controls {{
      margin-top: 1em;
      display: flex;
      gap: 1em;
      align-items: center;
    }}
    input, button {{
      background-color: #222;
      color: white;
      border: 1px solid #555;
      padding: 0.4em 0.8em;
      font-size: 1em;
    }}
    input[type="range"] {{
      width: 300px;
    }}
    .time-display {{
      font-family: monospace;
      min-width: 80px;
      text-align: center;
    }}
  </style>
</head>
<body>
  <svg id="svg" viewBox="0 0 {svg_size} {svg_size}" xmlns="http://www.w3.org/2000/svg">
    <path d="{path_data}" fill="none" stroke="#444" stroke-width="1" />
    <path id="animatedPath" d="{path_data}" fill="none" stroke="white" stroke-width="1"
          stroke-dasharray="{path_length:.2f}" stroke-dashoffset="{path_length:.2f}" />
  </svg>
  <div class="controls">
    Duration (s):
    <input type="number" id="durationInput" min="1" max="300" step="1" value="{duration}">
    <button id="playPauseBtn">▶️</button>
    <button id="restartBtn">⟲</button>
    <input id="scrubber" type="range" min="0" max="{duration}" step="0.01" value="0">
    <span id="timeDisplay" class="time-display">00:00</span>
  </div>
  <script>
    const path = document.getElementById("animatedPath");
    const scrubber = document.getElementById("scrubber");
    const playPauseBtn = document.getElementById("playPauseBtn");
    const restartBtn = document.getElementById("restartBtn");
    const durationInput = document.getElementById("durationInput");
    const timeDisplay = document.getElementById("timeDisplay");

    let duration = parseFloat(durationInput.value);
    let pathLength = parseFloat(path.getAttribute("stroke-dasharray"));
    let playing = false;
    let startTime = null;
    let pausedAt = 0;
    let rafId = null;

    function formatTime(seconds) {{
      const m = Math.floor(seconds / 60);
      const s = Math.floor(seconds % 60);
      return `${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}`;
    }}

    function setTime(t) {{
      const offset = pathLength * (1 - t / duration);
      path.setAttribute("stroke-dashoffset", offset);
      scrubber.value = t.toFixed(2);
      timeDisplay.textContent = formatTime(t);
    }}

    function animate(timestamp) {{
      if (!startTime) startTime = timestamp;
      const elapsed = (timestamp - startTime) / 1000;
      const currentTime = Math.min(pausedAt + elapsed, duration);
      setTime(currentTime);
      if (currentTime < duration) {{
        rafId = requestAnimationFrame(animate);
      }} else {{
        playing = false;
        pausedAt = 0;
        playPauseBtn.textContent = "▶️";
      }}
    }}

    function play() {{
      if (!playing) {{
        playing = true;
        playPauseBtn.textContent = "⏸";
        startTime = null;
        rafId = requestAnimationFrame(animate);
      }}
    }}

    function pause() {{
      if (playing) {{
        cancelAnimationFrame(rafId);
        pausedAt = parseFloat(scrubber.value);
        playPauseBtn.textContent = "▶️";
        playing = false;
      }}
    }}

    function togglePlayPause() {{
      if (playing) {{
        pause();
      }} else {{
        startTime = null;
        play();
      }}
    }}

    function restart() {{
      cancelAnimationFrame(rafId);
      playing = false;
      pausedAt = 0;
      setTime(0);
      play();
    }}

    playPauseBtn.addEventListener("click", togglePlayPause);
    restartBtn.addEventListener("click", restart);

    scrubber.addEventListener("input", () => {{
      pause();
      pausedAt = parseFloat(scrubber.value);
      setTime(pausedAt);
    }});

    durationInput.addEventListener("change", () => {{
      duration = parseFloat(durationInput.value);
      scrubber.max = duration;
      if (playing) {{
        pause();
        pausedAt = 0;
        setTime(0);
        play();
      }}
    }});

    setTime(0);
  </script>
</body>
</html>"""

def make_live_track(input_file: str, duration: float = 10.0) -> None:
    """Generate live track visualization with HTML animation."""
    if not os.path.isfile(input_file):
        print(f"Error: '{input_file}' not found.", file=sys.stderr)
        sys.exit(1)
    
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # Read and process data
    df = pd.read_csv(input_file, sep=r"\s+", names=['rho', 'rad'], comment='#')
    total = len(df)
    if total == 0:
        print("Error: No data to plot.", file=sys.stderr)
        sys.exit(1)
    
    # Process data in 5% increments
    for pct in range(5, 101, 5):
        count_cur = math.ceil(total * pct / 100)
        count_prev = math.ceil(total * (pct - 5) / 100)
        
        # Get coordinates for current segment
        coords = []
        for _, row in df.iloc[:count_cur].iterrows():
            x, y = polar_to_cartesian(row['rad'], row['rho'] + OFFSET)
            coords.append((x, y))
        
        # Generate SVG path and HTML
        path_data, points = generate_svg_path(coords, SVG_SIZE)
        path_length = calculate_path_length(points)
        
        # Generate HTML file
        html_content = generate_html(path_data, path_length, duration, SVG_SIZE)
        filename = f"file{pct:03d}.html"
        with open(os.path.join(OUT_DIR, filename), 'w') as f:
            f.write(html_content)
        
        print(f"→ {filename} ({pct}% plotted)")

if __name__ == '__main__':
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
    make_live_track(INPUT_FILE, duration) 