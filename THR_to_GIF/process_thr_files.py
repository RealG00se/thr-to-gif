#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def process_file(input_path, output_path):
    """Process a single file to remove duplicate consecutive lines."""
    prev = None
    
    with open(input_path) as f_in, open(output_path, 'w') as f_out:
        for line in f_in:
            line_str = line.rstrip('\n')
            if line_str == prev:
                continue
            f_out.write(line)
            prev = line_str

def process_directory(input_dir, output_dir=None):
    """Process all .thr files in the input directory."""
    input_path = Path(input_dir)
    
    # If no output directory is specified, create a 'processed' subdirectory
    if output_dir is None:
        output_path = input_path / 'processed'
    else:
        output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Process all .thr files in the current directory only (ignoring subdirectories)
    thr_files = list(input_path.glob('*.thr'))
    
    if not thr_files:
        print(f"No .thr files found in {input_dir}")
        return
    
    print(f"Found {len(thr_files)} .thr files to process")
    
    for thr_file in thr_files:
        output_file = output_path / thr_file.name
        print(f"Processing {thr_file.name} -> {output_file.name}")
        process_file(thr_file, output_file)
    
    print(f"\nProcessing complete! Processed files are in: {output_path}")

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} input_directory [output_directory]")
        print("If output_directory is not specified, files will be saved in input_directory/processed")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a valid directory")
        sys.exit(1)
    
    process_directory(input_dir, output_dir)

if __name__ == "__main__":
    main() 