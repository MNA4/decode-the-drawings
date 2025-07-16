"""
Main script for Decode the Drawings project.
Tracks three colored balls in a video,
estimates their 3D positions,
computes the orientation of the triangle they form,
and infers the pen tip position for drawing.

Results are visualized and optionally saved.
"""

import numpy as np
import pygame as pg
from widgets import Root, ImageWidget, AxisWidget
from media import video_generator, audio_intensity
from image_processing import get_all_balls
from ball_vectors import (
    calibrate_focal_length,
    get_rays,
    compute_ts,
    get_orientation,
    orient_pos,
)

# ----------------------
# Configuration
# ----------------------
IGNORE_BALL_RADIUS = False  # If True, use the law of cosines; else, estimate from video
IGNORE_AUDIO = (
    False  # If True, use pen-y coordinate to detect pen-down; else, use audio
)
VIDEO_PATH = "videos/3.mp4"  # Path to input video
OUTPUT_FILENAME = "pixels.txt"  # Output file for pen tip coordinates
PADDING = 10  # Padding for UI widgets
FPS = 60  # Target frames per second
PIXEL_THRESHOLD = 80  # Threshold for ball detection (in percent)
AUDIO_THRESHOLD = 0.0013  # Threshold for pen-down audio detection
PEN_THRESHOLD = (
    1  # Threshold for pen tip y-coordinate to consider it touching the paper
)
INITIAL_Z = 18  # Initial Z distance (cm) for calibration
PEN_LENGTH = 18  # Length of the pen (cm)
INITIAL_DST = 9  # Initial distance between balls (cm)
INV_THRESHOLD = 100 / PIXEL_THRESHOLD  # Inverse threshold, precomputed for efficiency


def save_pixels(pixels, filename):
    """
    Save the pixel coordinates to a file.
    Args:
        pixels (list): List of pixel coordinates as tuples (x, y).
        filename (str): The name of the file to save the coordinates.
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(f"{i[0]} {i[1]}\n" for i in pixels)


# ----------------------
# Initialization
# ----------------------
video = video_generator(VIDEO_PATH)
frame_array, _ = next(video)  # Get first frame for setup

# Detect initial ball positions and radii
ball_projected_pos, ball_projected_radius = get_all_balls(frame_array, INV_THRESHOLD)

# Calibrate focal length using initial positions
focal_length = calibrate_focal_length(
    *ball_projected_pos, initial_z=INITIAL_Z, initial_dst=INITIAL_DST
)

# Estimate actual ball radius if not ignored
ball_actual_radius = None
if not IGNORE_BALL_RADIUS:
    # The balls may have a slightly different radius than assumed
    ball_actual_radius = ball_projected_radius * INITIAL_Z / focal_length

# Set up display and UI
width = frame_array.shape[0]
height = frame_array.shape[1]
screen = pg.display.set_mode((width, height))
root = Root(screen, padding=PADDING)
axis_widget = AxisWidget(root, x=None, y=None, z=None)
image_widget = ImageWidget(root, pixels=[], curr_pos=(0, 0))
root.update_layout()
clock = pg.time.Clock()
pixels = []  # List of pen tip positions

# ----------------------
# Main Loop
# ----------------------
STATUS = "computing"
while STATUS != "quit":
    for event in pg.event.get():
        if event.type == pg.QUIT:
            STATUS = "quit"
        root.process_event(event)

    if STATUS == "computing":
        try:
            frame_array, aud_array = next(video)
        except StopIteration:
            save_pixels(pixels, OUTPUT_FILENAME)
            STATUS = "saving"
            continue

        if not IGNORE_AUDIO:
            # Detect pen-down event using audio
            aud_intensity = audio_intensity(aud_array)
            if aud_intensity <= AUDIO_THRESHOLD:
                continue  # Skip frame if audio intensity is below threshold

        # Detect balls in current frame
        ball_projected_pos, ball_projected_radius = get_all_balls(
            frame_array, INV_THRESHOLD
        )

        # Compute 3D rays from camera to each ball
        ball_rays = get_rays(ball_projected_pos, width, height, focal_length)

        if IGNORE_BALL_RADIUS:
            # Use geometric constraint to solve for scale factors
            scale_factors = compute_ts(*ball_rays, INITIAL_DST)
        else:
            # Use projected and actual radii to solve for scale factors
            z = ball_actual_radius / ball_projected_radius * focal_length
            scale_factors = -z / ball_rays[:, 2]

        ball_actual_pos = ball_rays * scale_factors[:, np.newaxis]

        # Compute orientation of the triangle formed by the balls
        x_axis, y_axis, z_axis = get_orientation(
            ball_actual_pos[0], ball_actual_pos[1], ball_actual_pos[2]
        )
        # Camera position (opposite of average ball position)
        non_oriented_cam_pos = -np.mean(ball_actual_pos, axis=0)
        # Pen tip position in camera coordinates
        non_oriented_pen_tip = non_oriented_cam_pos - (0, PEN_LENGTH, 0)
        # Transform pen tip to triangle's local coordinate system
        pen_tip = orient_pos(non_oriented_pen_tip, x_axis, y_axis, z_axis)

        if IGNORE_AUDIO:
            if pen_tip[1] >= -PEN_LENGTH + PEN_THRESHOLD:
                continue
        pixels.append((pen_tip[0], pen_tip[2]))

        # Update UI widgets
        axis_widget.set_axes(x_axis, y_axis, z_axis)
        image_widget.set_data(pixels, (pen_tip[0], pen_tip[2]))

    # ----------------------
    # Drawing
    # ----------------------
    screen.blit(pg.surfarray.make_surface(frame_array), (0, 0))

    # Draw detected balls and triangle
    for j in range(3):
        pg.draw.circle(screen, (255, 255, 255), ball_projected_pos[j], 10)
        pg.draw.circle(
            screen, (255, 255, 255), ball_projected_pos[j], ball_projected_radius[j], 5
        )

    # Render UI widgets
    root.render()
    pg.display.flip()
    fps = clock.tick(FPS)
    pg.display.set_caption(f"FPS: {fps}")

pg.quit()
