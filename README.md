# thr-to-gif
Process a .thr file and output html animation with playback controls and GIF
Example usage: gif/run_thr_tool.sh your1.thr -d 20

Convert .thr file(s) to animated HTML and export as GIF

positional arguments:

  thr_files             Input .thr file(s)
  

options:

  -h, --help            show this help message and exit
  
  -o, --output OUTPUT   Output HTML filename (default: based on first .thr)
  
  -g, --gif GIF         Output GIF filename (default: based on first .thr)
  
  -d, --duration DURATION
            Animation duration in seconds
                        
  --size SIZE           Canvas size (default 1000x1000)
  
  --no-gif              Skip GIF export
  

Subfolder is created for output HTML and GIF files
