# Decode the Drawings Challenge

This project is a solution to Radu's "Decode the Drawing" challenge. It uses computer vision and audio processing to track three colored balls in a video, estimate their 3D positions, compute the orientation of the triangle they form, and infer the pen tip position for drawing. The results are visualized in a custom Pygame UI and optionally saved to a file.

## Features
- Tracks three colored balls in a video stream
- Estimates 3D positions and orientation using geometric methods
- Detects pen-down events using audio intensity
- Visualizes the drawing process and 3D axes in a custom Pygame UI
- Saves the pen tip coordinates to a text file

## Requirements
- Python 3.8+
- numpy
- pygame

Install dependencies with:
```cmd
pip install -r requirements.txt
```

## Usage
1. Place your input video (e.g., `3.mp4`) in the project directory.
2. Adjust configuration parameters in `script.py` if needed (e.g., `VIDEO_PATH`, `PIXEL_THRESHOLD`, etc).
3. Run the main script:
```cmd
python script.py
```
4. The UI will display the video, detected balls, and drawing. Pen tip coordinates are saved to `pixels.txt` when the video ends.

## File Overview
- `script.py` — Main application logic and UI
- `widgets.py` — Custom Pygame UI toolkit
- `image_processing.py` — Ball detection and image utilities
- `media.py` — Video and audio input utilities
- `ball_vectors.py` — 3D geometry and math utilities
- `requirements.txt` — Python dependencies

## Notes
- No OpenCV is required; all image processing is done with numpy and pygame.
- For best results, use a video with clear, well-separated colored balls and minimal background clutter.

## License
Copyright (c) 2025 @MNA4

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.