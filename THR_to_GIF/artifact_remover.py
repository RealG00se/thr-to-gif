#!/usr/bin/env python3
import math
import logging

def detect_constant_rho_segments(rhos, tol_rho=0.01, min_len=2):
    """
    Detects all contiguous segments where rho remains constant (±tol_rho)
    and of length >= min_len. Returns a list of tuples (start_idx, end_idx, rho_ref).
    """
    segments = []
    N = len(rhos)
    i = 0
    while i < N:
        if rhos[i] is None:
            i += 1
            continue
        rho_ref = rhos[i]
        j = i + 1
        while j < N and rhos[j] is not None and abs(rhos[j] - rho_ref) <= tol_rho:
            j += 1
        if j - i >= min_len:
            segments.append((i, j - 1, rho_ref))
        i = j
    return segments

def remove_full_circle_closing_point(input_path: str, output_path: str, tol_rho: float = 0.01) -> list:
    """
    Reads input_path, detects segments with constant radius and angle difference close to 2π,
    and removes only the last point of those segments if it closes the circle.
    """
    # Read file
    with open(input_path, 'r') as f:
        lines = f.readlines()
    
    thetas, rhos = [], []
    for line in lines:
        s = line.strip()
        if not s or s.startswith('#'):
            thetas.append(None)
            rhos.append(None)
        else:
            parts = s.replace(',', ' ').split()
            thetas.append(float(parts[0]))
            rhos.append(float(parts[1]))

    # Log initial statistics
    total_points = len([t for t in thetas if t is not None])
    logging.info(f"Total points in input file: {total_points}")

    # Detect all segments with constant rho
    segments = detect_constant_rho_segments(rhos, tol_rho=tol_rho, min_len=2)
    logging.info(f"Found {len(segments)} segments with constant radius")

    # Find segments that are close to full circles
    circle_segs = []
    for start, end, rho_ref in segments:
        th1 = thetas[start]
        th2 = thetas[end]
        if th1 is None or th2 is None:
            continue
        delta = th2 - th1
        # Normalize delta to [0, 2π]
        delta = delta % (2 * math.pi)
        # If delta is close to 2π, this is a full circle
        if abs(delta - 2 * math.pi) < 0.1:  # 0.1 rad ≈ 5.7 degrees
            circle_segs.append((start, end, delta))
            logging.info(f"Found circle segment at indices {start}→{end}, rho={rho_ref:.3f}, Δθ={delta:.3f} rad")

    # Remove only the last point of each full circle segment
    remove_indices = set()
    for start, end, _ in circle_segs:
        remove_indices.add(end)

    out_lines = []
    for i, line in enumerate(lines):
        if i in remove_indices:
            logging.info(f"Removing closing point at index {i}")
            continue
        out_lines.append(line)

    # Write output
    with open(output_path, 'w') as f:
        f.writelines(out_lines)

    # Log final statistics
    remaining_points = len([line for idx, line in enumerate(out_lines) if line.strip() and not line.strip().startswith('#')])
    logging.info(f"Points in output file: {remaining_points}")
    logging.info(f"Removed {len(remove_indices)} closing point(s) from full circles")

    return circle_segs

def process_thr_file(input_path: str, output_path: str) -> None:
    """
    Process a THR file to remove only the closing point of full circle artifacts and save the result.
    """
    try:
        circles = remove_full_circle_closing_point(input_path, output_path, tol_rho=0.01)
        if circles:
            logging.info(f"Removed closing point(s) from {len(circles)} full circle segment(s) in {input_path}")
            for idx, (st, ed, delta) in enumerate(circles, 1):
                logging.info(f" {idx}. indices {st}→{ed}, Δθ={delta:.4f} rad")
        else:
            logging.info(f"No full circle artifacts found in {input_path}")
    except Exception as e:
        logging.error(f"Error processing {input_path}: {e}")
        raise 