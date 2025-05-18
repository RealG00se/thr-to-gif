import math
import argparse
import subprocess
import sys
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import shutil

def polar_to_cartesian(r, theta):
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return x, y

def parse_thr_file(filename):
    coords = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) == 2:
                        theta = float(parts[0])
                        r = float(parts[1])
                        coords.append(polar_to_cartesian(r, theta))
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

def prettify_svg(svg_element):
    rough_string = tostring(svg_element, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def generate_html(svg_content, duration):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
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
      align-items: center;
      gap: 1em;
    }}
    button, input[type=range] {{
      appearance: none;
      background-color: #222;
      border: 1px solid #555;
      color: white;
      cursor: pointer;
      padding: 0.5em 1em;
      font-size: 1em;
    }}
    input[type=range] {{
      width: 300px;
      height: 6px;
      border-radius: 3px;
    }}
  </style>
</head>
<body>
  {svg_content}
  <div class="controls">
    <button onclick="playAnimation()">Play</button>
    <button onclick="pauseAnimation()">Pause</button>
    <button onclick="restartAnimation()">Restart</button>
    <input id="scrubber" type="range" min="0" max="{duration}" step="0.01" value="0" oninput="scrubToTime(this.value)" />
  </div>
  <script>
    const svg = document.querySelector("svg");
    const anim = document.getElementById("drawAnim");
    const scrubber = document.getElementById("scrubber");
    let scrubInterval = null;

    function playAnimation() {{
      svg.unpauseAnimations();
      scrubInterval = setInterval(() => {{
        const t = svg.getCurrentTime();
        scrubber.value = t.toFixed(2);
      }}, 30);
    }}

    function pauseAnimation() {{
      svg.pauseAnimations();
      clearInterval(scrubInterval);
    }}

    function restartAnimation() {{
      svg.setCurrentTime(0);
      playAnimation();
    }}

    function scrubToTime(t) {{
      svg.setCurrentTime(parseFloat(t));
    }}
  </script>
</body>
</html>
"""

def write_html(coords, output_file, svg_size=1000, duration=10):
    path_data, points = generate_svg_path(coords, svg_size)
    path_length = calculate_path_length(points)

    svg = Element('svg', viewBox=f"0 0 {svg_size} {svg_size}", xmlns='http://www.w3.org/2000/svg')

    SubElement(svg, 'path', {
        'd': path_data,
        'fill': 'none',
        'stroke': '#444',
        'stroke-width': '1'
    })

    animated_path = SubElement(svg, 'path', {
        'd': path_data,
        'fill': 'none',
        'stroke': 'white',
        'stroke-width': '1',
        'stroke-dasharray': f'{path_length:.2f}',
        'stroke-dashoffset': f'{path_length:.2f}'
    })

    SubElement(animated_path, 'animate', {
        'id': 'drawAnim',
        'attributeName': 'stroke-dashoffset',
        'from': f'{path_length:.2f}',
        'to': '0',
        'dur': f'{duration}s',
        'fill': 'freeze',
        'begin': '0s'
    })

    svg_str = prettify_svg(svg)
    html_str = generate_html(svg_str, duration)

    with open(output_file, 'w') as f:
        f.write(html_str)

def check_dependencies():
    for cmd in ['node', 'npm', 'ffmpeg']:
        if not shutil.which(cmd):
            print(f"[ERROR] Required command '{cmd}' not found in your PATH.")
            sys.exit(1)

def run_capture(html_file, output_gif, duration):
    # Always resolve path to capture.js next to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    capture_path = os.path.join(script_dir, 'capture.js')

    if not os.path.isfile(capture_path):
        print("Error: 'capture.js' not found.")
        sys.exit(1)

    cmd = ['node', capture_path, html_file, output_gif, str(duration)]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: capture.js failed with {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Convert .thr file(s) to animated HTML and export as GIF"
    )
    parser.add_argument('thr_files', nargs='+', help="Input .thr file(s)")
    parser.add_argument('-o', '--output', help="Output HTML filename (default: based on first .thr)")
    parser.add_argument('-g', '--gif', help="Output GIF filename (default: based on first .thr)")
    parser.add_argument('-d', '--duration', type=int, default=10, help="Animation duration in seconds")
    parser.add_argument('--size', type=int, default=1000, help="Canvas size (default 1000x1000)")
    parser.add_argument('--no-gif', action='store_true', help="Skip GIF export")

    args = parser.parse_args()

    if not args.thr_files:
        print("Error: At least one .thr file is required.")
        sys.exit(1)

    all_coords = []
    for f in args.thr_files:
        if not os.path.isfile(f):
            print(f"Error: File '{f}' not found.")
            sys.exit(1)
        coords = parse_thr_file(f)
        all_coords.extend(coords)

    base_name = os.path.splitext(os.path.basename(args.thr_files[0]))[0]
    output_dir = base_name
    os.makedirs(output_dir, exist_ok=True)

    html_name = args.output if args.output else os.path.join(output_dir, f"{base_name}.html")
    gif_name = args.gif if args.gif else os.path.join(output_dir, f"{base_name}.gif")

    write_html(all_coords, html_name, args.size, args.duration)
    print(f"HTML animation saved to {html_name}")

    if args.no_gif:
        print("GIF export skipped (--no-gif specified).")
        return

    check_dependencies()
    print(f"Exporting to GIF: {gif_name} ...")
    run_capture(html_name, gif_name, args.duration)
    print(f"GIF export completed: {gif_name}")

if __name__ == '__main__':
    main()