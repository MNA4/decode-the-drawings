"""
Main script for Decode the Drawings project.
Tracks three colored balls in a video,
estimates their 3D positions,
computes the orientation of the triangle they form,
and infers the pen tip position for drawing.

Results are visualized and optionally saved.
"""

import time
import numpy as np
import pygame as pg
from widgets import Root, ImageWidget, AxisWidget
from media import video_generator, audio_intensity
from image_processing import get_all_balls, threshold, get_tangential_points

from vectors import (
    calibrate_focal_length,
    get_rays,
    compute_ts,
    get_orientation,
    orient_pos,
    find_angle_bisectors
)

# ----------------------
# Configuration
# ----------------------
IGNORE_BALL_RADIUS = False  # If True, use the law of cosines; else, estimate from ball projected radius.
IGNORE_AUDIO = (
    False  # If True, use pen-y coordinate to detect pen-down; else, use audio intensity
)
CORRECT_ELLIPSE = True
USE_LINE_MASK = False
VIDEO_PATH = "videos/1.mp4"  # Path to input video
OUTPUT_FILENAME = "pixels.txt"  # Output file for pen tip coordinates
PADDING = 10  # Padding for UI widgets
FPS = 60  # Target frames per second
PIXEL_SATURATION_THRESHOLD = 75  # Threshold for ball detection (in percent)
PIXEL_LIGHTNESS_THRESHOLD = 90  # Threshold for lightness detection (0-255)
AUDIO_THRESHOLD = 0.0013  # Threshold for pen-down audio detection
PEN_THRESHOLD = (
    1  # Threshold for pen tip y-coordinate to consider it touching the paper
)
INITIAL_Z = 18  # Initial Z distance (cm) for calibration
PEN_LENGTH = 18  # Length of the pen (cm)
INITIAL_DST = 9  # Initial distance between balls (cm)
INV_SATURATION_THRESHOLD = 100 / PIXEL_SATURATION_THRESHOLD


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
threshold_array = threshold(
    frame_array, INV_SATURATION_THRESHOLD, PIXEL_LIGHTNESS_THRESHOLD
)
ball_projected_pos, ball_projected_radius = get_all_balls(threshold_array)

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
axis_widget = AxisWidget(
    root, x=np.array((1, 0, 0)), y=np.array((0, 1, 0)), z=np.array((0, 0, 0))
)
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

        pen_down = True
        if not IGNORE_AUDIO:
            # Detect pen-down event using audio
            aud_intensity = audio_intensity(aud_array)
            if aud_intensity < AUDIO_THRESHOLD:
                pen_down = False
                
        # Detect balls in current frame
        threshold_array = threshold(
            frame_array, INV_SATURATION_THRESHOLD, PIXEL_LIGHTNESS_THRESHOLD
        )
        if CORRECT_ELLIPSE:
            ball_tangential_points = get_tangential_points(threshold_array, USE_LINE_MASK)
            rays, lengths = find_angle_bisectors(ball_tangential_points[:,0,:],
                                                ball_tangential_points[:,1,:],
                                                width,
                                                height,
                                                focal_length,
                                                ball_actual_radius)
        else:
            ball_projected_pos, ball_projected_radius = get_all_balls(threshold_array)

        if pen_down:
            # Compute 3D rays from camera to each ball
            if CORRECT_ELLIPSE:
                ball_rays = rays
            else:
                ball_rays = get_rays(ball_projected_pos, width, height, focal_length)

            if IGNORE_BALL_RADIUS:
                # Use geometric constraint to solve for scale factors
                scale_factors = compute_ts(*ball_rays, INITIAL_DST)
            else:
                if CORRECT_ELLIPSE:
                    scale_factors = lengths
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

            # Update UI widgets
            axis_widget.set_axes(x_axis, y_axis, z_axis)
            image_widget.set_data(pixels, (pen_tip[0], pen_tip[2]))

            if IGNORE_AUDIO:
                if pen_tip[1] >= -PEN_LENGTH + PEN_THRESHOLD:
                    pen_down = False

        if pen_down:
            pixels.append((pen_tip[0], pen_tip[2]))

    # ----------------------
    # Drawing
    # ----------------------
    display_array = (threshold_array * 255).astype(np.uint8)
    pg.surfarray.blit_array(screen, display_array)

    # Draw detected balls and triangle
    # for j in range(3):
    #     pg.draw.circle(screen, (255, 255, 255), ball_projected_pos[j], 10)
    #     pg.draw.circle(
    #         screen, (255, 255, 255), ball_projected_pos[j], ball_projected_radius[j], 5
    #     )
    for j in ball_tangential_points:
        for k in j:
            pg.draw.circle(screen, (255, 255, 255), k, 10, 2)
    # Render UI widgets
    root.render()
    pg.display.flip()
    clock.tick(FPS)

    pg.display.set_caption(f"FPS: {clock.get_fps():.2f} | Status: {STATUS}")

pg.quit()
