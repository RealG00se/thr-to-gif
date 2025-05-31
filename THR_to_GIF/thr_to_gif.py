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
from artifact_remover import process_thr_file

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('thr_converter.log', mode='w'),  # Use 'w' mode to overwrite the file each time
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

def generate_svg_path(coords: List[Tuple[float, float]], svg_size: int, rotation_deg: float = 0.0) -> Tuple[str, List[Tuple[float, float]]]:
    """Generate SVG path data from coordinates and scale to fit SVG size, with optional rotation in degrees."""
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
    
    # Convert rotation to radians
    rotation_rad = math.radians(rotation_deg)
    cos_r = math.cos(rotation_rad)
    sin_r = math.sin(rotation_rad)
    
    # Scale, center, and rotate points
    scaled_points = []
    for x, y in coords:
        # Center and scale
        centered_x = (x - center_x) * scale
        centered_y = (y - center_y) * scale
        # Apply rotation
        rotated_x = centered_x * cos_r - centered_y * sin_r
        rotated_y = centered_x * sin_r + centered_y * cos_r
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

def run_capture(html_file: str, output_gif: Optional[str], duration: float, no_png: bool = False) -> None:
    """Run the capture process to create GIF and/or PNG."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        capture_path = os.path.join(script_dir, 'capture.js')
        
        if not os.path.isfile(capture_path):
            raise FileNotFoundError("capture.js not found")
        
        # Construct command based on whether we want GIF output
        if output_gif is not None:  # Explicitly check for None
            cmd = ['node', capture_path, html_file, output_gif, str(duration)]
            if no_png:
                cmd.append('--no-png')
            print(f"\n🎬 Starting GIF generation for: {os.path.basename(html_file)}")
            print(f"   Duration: {duration}s | Output: {os.path.basename(output_gif)}")
        else:
            # PNG-only mode: use a special marker value
            cmd = ['node', capture_path, html_file, 'NO_GIF', str(duration)]
            print(f"\n📸 Creating PNG preview for: {os.path.basename(html_file)}")
            
        # Log the command for debugging
        print(f"\n🔍 PYTHON: Running command: {' '.join(cmd)}")
        
        # Run the command with real-time output (don't capture stdout so progress bars show)
        # but capture stderr for error handling
        result = subprocess.run(cmd, check=True, stderr=subprocess.PIPE, text=True)
        
        # Print any error output from capture.js
        if result.stderr:
            print("\n🔍 CAPTURE.JS STATUS:")
            print(result.stderr)
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running capture.js: {e}")
        if e.stderr:
            print("\n🔍 CAPTURE.JS ERRORS:")
            print(e.stderr)
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error during capture: {e}")
        raise

def write_html(coords: List[Tuple[float, float]], output_file: str, svg_size: int = 1000, duration: float = 10.0, rotation_deg: float = 0.0) -> None:
    """Write HTML animation file with SVG path."""
    path_data, points = generate_svg_path(coords, svg_size, rotation_deg)
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

def write_svg(coords: List[Tuple[float, float]], output_file: str, svg_size: int = 1000, rotation_deg: float = 0.0) -> None:
    """Write standalone SVG file with the path."""
    path_data, _ = generate_svg_path(coords, svg_size, rotation_deg)
    
    svg_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{svg_size}" height="{svg_size}" viewBox="0 0 {svg_size} {svg_size}" xmlns="http://www.w3.org/2000/svg">
    <path d="{path_data}" fill="none" stroke="black" stroke-width="1" />
</svg>"""

    with open(output_file, 'w') as f:
        f.write(svg_content)

def cleanup_temp_files():
    """Clean up any temporary files that might have been left behind."""
    try:
        # Clean up any frames directories
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for item in os.listdir(current_dir):
            if item.startswith('frames_'):
                full_path = os.path.join(current_dir, item)
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path, ignore_errors=True)
                    logging.info(f"Cleaned up temporary directory: {item}")
        # Clean up palette file
        palette_file = os.path.join(current_dir, 'palette.png')
        if os.path.exists(palette_file):
            os.remove(palette_file)
            logging.info("Cleaned up palette file")
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description='Convert THR file to GIF animation')
    parser.add_argument('input_file', help='Input THR or HTML file')
    parser.add_argument('-d', '--duration', type=float, default=10.0,
                      help='Animation duration in seconds (default: 10.0)')
    parser.add_argument('-s', '--size', type=int, default=1000,
                      help='SVG size in pixels (default: 1000)')
    parser.add_argument('-r', '--rotation', type=float, default=0.0,
                      help='Rotation in degrees (default: 0)')
    parser.add_argument('--no-gif', action='store_true',
                      help='Skip GIF generation, only create HTML and PNG')
    parser.add_argument('--no-svg', action='store_true',
                      help='Skip SVG generation')
    parser.add_argument('--no-html', action='store_true',
                      help='Skip HTML animation generation')
    parser.add_argument('--no-png', action='store_true',
                      help='Skip PNG preview generation (also skips GIF)')
    parser.add_argument('--html-to-gif', action='store_true',
                      help='Process existing HTML files to generate GIFs')
    args = parser.parse_args()

    try:
        # Log the arguments for debugging
        logging.info(f"🔍 DEBUG: Arguments: no_gif={args.no_gif}, no_svg={args.no_svg}, no_html={args.no_html}, no_png={args.no_png}, html_to_gif={args.html_to_gif}")

        if args.html_to_gif:
            # HTML-to-GIF mode: process existing HTML file
            if not args.input_file.endswith('.html'):
                logging.error("In --html-to-gif mode, input file must be an HTML file")
                sys.exit(1)
            
            if not os.path.exists(args.input_file):
                logging.error(f"HTML file not found: {args.input_file}")
                sys.exit(1)
            
            print(f"\n🔄 Processing HTML file: {os.path.basename(args.input_file)}")
            
            # Use the HTML file directly
            html_file = args.input_file
            base_name = os.path.splitext(os.path.basename(html_file))[0]
            output_dir = os.path.dirname(html_file)
            
            # Generate output files in the same directory as the HTML file
            gif_file = None if args.no_gif else os.path.join(output_dir, f"{base_name}.gif")
            png_file = os.path.join(output_dir, f"{base_name}.png")
            
            # Log the file paths for debugging
            logging.info(f"🔍 DEBUG: HTML-to-GIF mode - html={html_file}, gif={gif_file}, png={png_file}")
            
            # Run capture process if we need either GIF or PNG
            if gif_file is not None or not args.no_png:
                run_capture(html_file, gif_file, args.duration, args.no_png)
                if not args.no_png:
                    print(f"✅ Created PNG preview: {os.path.basename(png_file)}")
                if gif_file is not None:
                    print(f"✅ Created GIF animation: {os.path.basename(gif_file)}")
            else:
                print("⚠️  Both GIF and PNG generation disabled - nothing to do")
            
            print("🎉 HTML-to-GIF conversion completed successfully!")
        
        else:
            # Normal THR-to-outputs mode
            if not args.input_file.endswith('.thr'):
                logging.error("In normal mode, input file must be a THR file")
                sys.exit(1)
            
            print(f"\n🔄 Processing THR file: {os.path.basename(args.input_file)}")
            
            # Create output directory
            base_name = os.path.splitext(os.path.basename(args.input_file))[0]
            output_dir = os.path.join(os.path.dirname(args.input_file), base_name)
            ensure_dir_exists(output_dir)

            # Process the THR file to remove circle artifacts
            print("🔧 Step 1/5: Processing THR file and removing artifacts...")
            artifact_removed_thr = os.path.join(output_dir, f"{base_name}.thr")
            process_thr_file(args.input_file, artifact_removed_thr)
            logging.info(f"Created artifact-removed THR file: {artifact_removed_thr}")

            # Parse the cleaned THR file
            print("📊 Step 2/5: Parsing coordinates...")
            coords = parse_thr_file(artifact_removed_thr)

            # Generate output files
            html_file = os.path.join(output_dir, f"{base_name}.html")
            gif_file = None if args.no_gif else os.path.join(output_dir, f"{base_name}.gif")
            png_file = os.path.join(output_dir, f"{base_name}.png")
            svg_file = os.path.join(output_dir, f"{base_name}.svg")

            # Log the file paths for debugging
            logging.info(f"🔍 DEBUG: Output files: html={html_file}, gif={gif_file}, png={png_file}, svg={svg_file}")

            # Write HTML animation (pass rotation)
            if not args.no_html:
                print("📝 Step 3/5: Generating HTML animation...")
                write_html(coords, html_file, args.size, args.duration, args.rotation)
                print(f"✅ Created HTML animation: {os.path.basename(html_file)}")

            # Write SVG file if not disabled
            if not args.no_svg:
                print("🎨 Step 4/5: Generating SVG file...")
                write_svg(coords, svg_file, args.size, args.rotation)
                print(f"✅ Created SVG file: {os.path.basename(svg_file)}")

            # Run capture process (this will create both GIF and PNG)
            if not args.no_png:
                print("🎬 Step 5/5: Generating visual outputs...")
                run_capture(html_file, gif_file, args.duration, args.no_png)
                if not args.no_png:
                    print(f"✅ Created PNG preview: {os.path.basename(png_file)}")
                if gif_file is not None:
                    print(f"✅ Created GIF animation: {os.path.basename(gif_file)}")

            print("🎉 Conversion completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during conversion: {e}")
        logging.error(f"Error during conversion: {e}")
        sys.exit(1)
    finally:
        # Always clean up temporary files
        cleanup_temp_files()

if __name__ == "__main__":
    main()