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
![Tyler-Foust-Wave](https://github.com/user-attachments/assets/591fef8e-eb94-46a7-a626-a8bf556dcde8)
![LongwoodWarrenHants](https://github.com/user-attachments/assets/6bb4f262-08fe-4400-abfa-a2d073073681)
![clear_from_in_Ultra](https://github.com/user-attachments/assets/785ae810-7173-4525-8c8a-5042c255de7c)

