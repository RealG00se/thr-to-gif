import math
import argparse
import subprocess
import sys
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import shutil
from typing import List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('thr_converter.log'),
        logging.StreamHandler()
    ]
)

def polar_to_cartesian(r: float, theta: float) -> Tuple[float, float]:
    """Convert polar coordinates to cartesian coordinates."""
    try:
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        return x, y
    except Exception as e:
        logging.error(f"Error converting polar coordinates: {e}")
        raise

def parse_thr_file(filename: str) -> List[Tuple[float, float]]:
    """Parse a THR file and return a list of cartesian coordinates."""
    coords = []
    try:
        with open(filename, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip() or line.strip().startswith('#'):
                    continue
                
                parts = line.strip().split()
                if len(parts) != 2:
                    logging.warning(f"Line {line_num} in {filename} has invalid format: {line.strip()}")
                    continue
                
                try:
                    theta = float(parts[0])
                    r = float(parts[1])
                    
                    # Normalize theta to [-π, π] range
                    theta = theta % (2 * math.pi)
                    if theta > math.pi:
                        theta -= 2 * math.pi
                    
                    if r < 0:
                        logging.warning(f"Line {line_num}: negative radius value {r}")
                        continue
                    
                    coords.append(polar_to_cartesian(r, theta))
                except ValueError as e:
                    logging.warning(f"Line {line_num}: invalid number format: {e}")
                    continue
                
    except Exception as e:
        logging.error(f"Error reading {filename}: {e}")
        raise
    
    if not coords:
        logging.error(f"No valid coordinates found in {filename}")
        raise ValueError(f"No valid coordinates found in {filename}")
    
    return coords

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
    
    # Scale and translate points, rotating 90 degrees counterclockwise
    scaled_points = []
    for x, y in coords:
        # First center and scale
        centered_x = (x - center_x) * scale
        centered_y = (y - center_y) * scale
        # Then rotate 90 degrees counterclockwise (x,y) -> (y,-x)
        rotated_x = centered_y
        rotated_y = -centered_x
        # Finally translate to center of SVG
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
        dx = x2 - x1
        dy = y2 - y1
        total_length += math.sqrt(dx * dx + dy * dy)
    
    return total_length

def ensure_dir_exists(path: str) -> None:
    """Ensure a directory exists, creating it if necessary."""
    if not os.path.exists(path):
        os.makedirs(path)

def check_dependencies() -> None:
    """Check if all required dependencies are installed."""
    missing_deps = []
    for cmd in ['node', 'npm', 'ffmpeg']:
        if not shutil.which(cmd):
            missing_deps.append(cmd)
    
    if missing_deps:
        logging.error(f"Missing required dependencies: {', '.join(missing_deps)}")
        raise RuntimeError(f"Missing required dependencies: {', '.join(missing_deps)}")

def run_capture(html_file: str, output_gif: str, duration: float) -> None:
    """Run the capture process to create GIF."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        capture_path = os.path.join(script_dir, 'capture.js')
        
        if not os.path.isfile(capture_path):
            raise FileNotFoundError("capture.js not found")
        
        cmd = ['node', capture_path, html_file, output_gif, str(duration)]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running capture.js: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error during capture: {e}")
        raise

def write_html(coords: List[Tuple[float, float]], output_file: str, svg_size: int = 1000, duration: float = 10.0) -> None:
    """Write HTML animation file with SVG path."""
    path_data, points = generate_svg_path(coords, svg_size)
    path_length = calculate_path_length(points)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Sand Table Animation</title>
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
      max-width: 90vw;
      max-height: 90vh;
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
    .time-input {{
      display: flex;
      align-items: center;
      gap: 0.2em;
    }}
    .time-input input {{
      width: 40px;
      text-align: center;
      font-family: monospace;
    }}
    .time-input span {{
      font-family: monospace;
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
    Duration:
    <div class="time-input">
      <input type="number" id="hours" min="0" max="23" value="0" onchange="updateDuration()">
      <span>:</span>
      <input type="number" id="minutes" min="0" max="59" value="0" onchange="updateDuration()">
      <span>:</span>
      <input type="number" id="seconds" min="0" max="59" value="{int(duration)}" onchange="updateDuration()">
    </div>
    <button id="playPauseBtn">▶️</button>
    <button id="restartBtn">⟲</button>
    <input id="scrubber" type="range" min="0" max="{duration}" step="0.01" value="0">
    <span id="timeDisplay" class="time-display">00:00:00</span>
  </div>
  <script>
    const path = document.getElementById("animatedPath");
    const scrubber = document.getElementById("scrubber");
    const playPauseBtn = document.getElementById("playPauseBtn");
    const restartBtn = document.getElementById("restartBtn");
    const hoursInput = document.getElementById("hours");
    const minutesInput = document.getElementById("minutes");
    const secondsInput = document.getElementById("seconds");
    const timeDisplay = document.getElementById("timeDisplay");

    let duration = parseFloat(secondsInput.value);
    let pathLength = parseFloat(path.getAttribute("stroke-dasharray"));
    let playing = false;
    let startTime = null;
    let pausedAt = 0;
    let rafId = null;

    function formatTime(seconds) {{
      const h = Math.floor(seconds / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      const s = Math.floor(seconds % 60);
      return `${{h.toString().padStart(2, '0')}}:${{m.toString().padStart(2, '0')}}:${{s.toString().padStart(2, '0')}}`;
    }}

    function parseTimeInput() {{
      const hours = parseInt(hoursInput.value) || 0;
      const minutes = parseInt(minutesInput.value) || 0;
      const seconds = parseInt(secondsInput.value) || 0;
      return hours * 3600 + minutes * 60 + seconds;
    }}

    function updateDuration() {{
      const newDuration = parseTimeInput();
      if (newDuration > 0) {{
        duration = newDuration;
        scrubber.max = duration;
        if (playing) {{
          pause();
          pausedAt = 0;
          setTime(0);
          play();
        }}
      }}
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

    setTime(0);
  </script>
</body>
</html>"""

    with open(output_file, 'w') as f:
        f.write(html_content)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert .thr file(s) to animated HTML and export as GIF"
    )
    parser.add_argument('thr_files', nargs='+', help="Input .thr file(s)")
    parser.add_argument('-o', '--output', help="Output HTML filename (default: based on first .thr)")
    parser.add_argument('-g', '--gif', help="Output GIF filename (default: based on first .thr)")
    parser.add_argument('-d', '--duration', type=float, default=10.0, help="Animation duration in seconds")
    parser.add_argument('--size', type=int, default=1000, help="Canvas size (default 1000x1000)")
    parser.add_argument('--no-gif', action='store_true', help="Skip GIF export")
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                      help="Set the logging level")

    args = parser.parse_args()
    logging.getLogger().setLevel(args.log_level)

    try:
        if not args.thr_files:
            raise ValueError("At least one .thr file is required")

        # Validate input files
        for f in args.thr_files:
            if not os.path.isfile(f):
                raise FileNotFoundError(f"File '{f}' not found")
            if not f.lower().endswith('.thr'):
                logging.warning(f"File '{f}' does not have .thr extension")

        # Validate duration
        if args.duration <= 0:
            raise ValueError("Duration must be positive")
        if args.duration > 43200:  # 12 hours
            logging.warning("Duration exceeds 12 hours, this may cause performance issues")

        # Validate canvas size
        if args.size <= 0:
            raise ValueError("Canvas size must be positive")
        if args.size > 4096:
            logging.warning("Large canvas size may cause performance issues")

        all_coords = []
        for f in args.thr_files:
            coords = parse_thr_file(f)
            all_coords.extend(coords)

        # Get the directory of the first THR file
        first_thr_dir = os.path.dirname(os.path.abspath(args.thr_files[0]))
        base_name = os.path.splitext(os.path.basename(args.thr_files[0]))[0]
        output_dir = os.path.join(first_thr_dir, base_name)
        ensure_dir_exists(output_dir)

        html_name = args.output if args.output else os.path.join(output_dir, f"{base_name}.html")
        gif_name = args.gif if args.gif else os.path.join(output_dir, f"{base_name}.gif")

        write_html(all_coords, html_name, args.size, args.duration)
        logging.info(f"HTML animation saved to {html_name}")

        if not args.no_gif:
            check_dependencies()
            logging.info(f"Exporting to GIF: {gif_name} ...")
            run_capture(html_name, gif_name, args.duration)
            logging.info(f"GIF export completed: {gif_name}")

    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()