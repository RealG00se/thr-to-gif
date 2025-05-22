import math
import argparse
import subprocess
import sys
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import shutil
from datetime import datetime

LOG_DIR = "logs"

def polar_to_cartesian(r, theta):
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return x, y

def parse_thr_file(filename):
    coords = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    parts = line.strip().split()
                    if len(parts) == 2:
                        try:
                            theta = float(parts[0])
                            r = float(parts[1])
                            coords.append(polar_to_cartesian(r, theta))
                        except ValueError:
                            print(f"Warning: skipping malformed line in {filename}: {line.strip()}")
                    else:
                        print(f"Warning: skipping malformed line in {filename}: {line.strip()}")
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        sys.exit(1)
    return coords

def generate_svg_path(coords, svg_size=1000):
    center = svg_size / 2
    scale = center
    path_data = []
    points = []
    for i, (x, y) in enumerate(coords):
        px = center + x * scale
        py = center - y * scale
        points.append((px, py))
        cmd = "M" if i == 0 else "L"
        path_data.append(f"{cmd} {px:.2f},{py:.2f}")
    return " ".join(path_data), points

def calculate_path_length(points):
    total = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i-1][0]
        dy = points[i][1] - points[i-1][1]
        total += math.hypot(dx, dy)
    return total

def generate_html(path_data, path_length, duration):
    return f"""<!DOCTYPE html>
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
    input[type="number"] {{
      width: 60px;
    }}
  </style>
</head>
<body>
  <svg id="svg" viewBox="0 0 1000 1000" xmlns="http://www.w3.org/2000/svg">
    <path d="{path_data}" fill="none" stroke="#444" stroke-width="1" />
    <path id="animatedPath" d="{path_data}" fill="none" stroke="white" stroke-width="1"
          stroke-dasharray="{path_length:.2f}" stroke-dashoffset="{path_length:.2f}" />
  </svg>
  <div class="controls">
    Duration (s):
    <input id="durationInput" type="number" min="1" max="300" step="1" value="{duration}">
    <button id="playPauseBtn">▶️</button>
    <button id="restartBtn">⟲</button>
    <input id="scrubber" type="range" min="0" max="{duration}" step="0.01" value="0">
  </div>
  <script>
    const path = document.getElementById("animatedPath");
    const scrubber = document.getElementById("scrubber");
    const playPauseBtn = document.getElementById("playPauseBtn");
    const restartBtn = document.getElementById("restartBtn");
    const durationInput = document.getElementById("durationInput");

    let duration = parseFloat(durationInput.value);
    let pathLength = parseFloat(path.getAttribute("stroke-dasharray"));
    let playing = false;
    let startTime = null;
    let pausedAt = 0;
    let rafId = null;

    function setTime(t) {{
      const offset = pathLength * (1 - t / duration);
      path.setAttribute("stroke-dashoffset", offset);
      scrubber.value = t.toFixed(2);
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
</html>
"""

def write_html(coords, output_file, svg_size=1000, duration=10):
    path_data, points = generate_svg_path(coords, svg_size)
    path_length = calculate_path_length(points)
    html_str = generate_html(path_data, path_length, duration)
    with open(output_file, 'w') as f:
        f.write(html_str)

def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def write_log(log_message):
    ensure_dir_exists(LOG_DIR)
    now = datetime.now()
    log_filename = os.path.join(LOG_DIR, f"log_{now.strftime('%Y-%m')}.txt")
    timestamp = now.strftime("[%Y-%m-%d %H:%M:%S]")
    with open(log_filename, 'a') as log_file:
        log_file.write(f"{timestamp} {log_message}\n")

def check_dependencies():
    for cmd in ['node', 'npm', 'ffmpeg']:
        if not shutil.which(cmd):
            print(f"[ERROR] Required command '{cmd}' not found in your PATH.")
            sys.exit(1)

def run_capture(html_file, output_gif, duration, png_file, force_overwrite):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    capture_path = os.path.join(script_dir, 'capture.js')
    if not os.path.isfile(capture_path):
        print("Error: 'capture.js' not found.")
        sys.exit(1)

    if not force_overwrite and os.path.isfile(output_gif) and os.path.isfile(png_file):
        print(f"⏩ Skipping capture (GIF & PNG exist): {output_gif}")
        return

    cmd = ['node', capture_path, html_file, output_gif, str(duration)]
    try:
        subprocess.run(cmd, check=True)
        if os.path.exists(png_file):
            print(f"🖼️  PNG preview saved: {png_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error: capture.js failed with {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Convert .thr to HTML + GIF + PNG (JS animation)")
    parser.add_argument('thr_files', nargs='+', help="Input .thr file(s) or folders")
    parser.add_argument('-d', '--duration', type=int, default=10, help="Animation duration in seconds")
    parser.add_argument('--size', type=int, default=1000, help="Canvas size in pixels")
    parser.add_argument('--no-gif', action='store_true', help="Skip GIF export")
    parser.add_argument('--force', action='store_true', help="Force overwrite of existing outputs")
    args = parser.parse_args()

    input_paths = []
    for path in args.thr_files:
        if os.path.isdir(path):
            input_paths.extend([os.path.join(path, f) for f in os.listdir(path) if f.endswith(".thr")])
        elif os.path.isfile(path) and path.endswith(".thr"):
            input_paths.append(path)
        else:
            print(f"⚠️ Skipped unrecognized input: {path}")

    if not input_paths:
        print("❌ No .thr files found.")
        sys.exit(1)

    check_dependencies()

    processed = skipped = failed = 0

    for i, thr_path in enumerate(input_paths):
        base = os.path.splitext(os.path.basename(thr_path))[0]
        output_dir = os.path.join(os.path.dirname(thr_path), base)
        os.makedirs(output_dir, exist_ok=True)

        html_file = os.path.join(output_dir, f"{base}.html")
        gif_file = os.path.join(output_dir, f"{base}.gif")
        png_file = os.path.join(output_dir, f"{base}.png")

        print(f"[{i+1}/{len(input_paths)}] Processing: {thr_path}")

        if not args.force and all(os.path.exists(p) for p in [html_file, gif_file, png_file]):
            print(f"⏩ Skipping {base} (already processed)")
            write_log(f"Skipped: {base}")
            skipped += 1
            continue

        coords = parse_thr_file(thr_path)
        try:
            write_html(coords, html_file, args.size, args.duration)
            print(f"✅ HTML saved: {html_file}")
        except Exception as e:
            print(f"❌ Failed to generate HTML: {e}")
            write_log(f"Failed HTML for {base}: {e}")
            failed += 1
            continue

        if not args.no_gif:
            try:
                run_capture(html_file, gif_file, args.duration, png_file, args.force)
                print(f"✅ GIF export completed: {gif_file}")
                write_log(f"Processed: {base}")
                processed += 1
            except Exception as e:
                print(f"❌ Capture failed: {e}")
                write_log(f"Capture failed for {base}: {e}")
                failed += 1
        else:
            print(f"⏭ Skipped GIF export")
            write_log(f"HTML only: {base}")
            processed += 1

    print(f"\n📊 Summary: {processed} processed, {skipped} skipped, {failed} failed.")

if __name__ == '__main__':
    main()