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
from widgets import Root, ImageWidget, AxisWidget, Checkboxes
from media import video_generator, audio_intensity
from image_processing import (
    get_all_balls,
    threshold,
    get_tangential_points,
    get_all_balls_weighted,
    render_ball,
)

from vectors import (
    calibrate_focal_length,
    get_rays,
    compute_ts,
    get_orientation,
    orient_pos,
    find_angle_bisectors,
    distance_from_area,
)

from smoothing import median_line_smoothing
# ----------------------
# Configuration
# ----------------------

# Input & Output Paths

VIDEO_PATH = "videos/3.mp4"  # Path to input video
OUTPUT_FILENAME = "pixels.txt"  # Output file for pen tip coordinates



# Ellipse Correction Method

TANGENTIAL_ELLIPSE_CORRECTION = False # If True, use tangential points for ellipse correction.
USE_LINE_MASK = True # Use a line mask for tangential ellipse correction

WEIGHTED_PIXELS_ELLIPSE_CORRECTION = True # If True, use weighted average for ellipse correction.



# Pen Down Detection Method

IGNORE_AUDIO = (
    False  # If True, use pen-y coordinate to detect pen-down; else, use audio intensity
)

AUDIO_THRESHOLD = 0.0013  # Threshold for pen-down audio detection
PEN_THRESHOLD = (
    1  # Threshold for pen tip y-coordinate to consider it touching the paper
)



# Camera-to-ball Distance Calculation Method

IGNORE_BALL_RADIUS = (
    False  # If True, use the law of cosines; else, estimate from ball projected radius.
)



# Frame Thresholding

PIXEL_SATURATION_THRESHOLD = 75  # Threshold for ball detection (in percent)
PIXEL_LIGHTNESS_THRESHOLD = 90  # Threshold for lightness detection (0-255)



# Smoothing Constant
SMOOTHING_CONSTANT = 1



# App Settings

PADDING = 10  # Padding for UI widgets
FPS = 60  # Target frames per second
DEBUG_BALLS = False
SKIP_FRAMES = 10
#DST_CALIB_CONSTANT = [1.00044347, 0.985, 0.99606536]
DST_CALIB_CONSTANT = [1, 0.99, 1]

# Setup dimensions

INITIAL_Z = 18  # Initial Z distance (between the camera & each balls) (cm)
PEN_LENGTH = 18  # Length of the pen (cm)
BALL_DST = 9  # Initial distance between balls (cm)
BALL_RADIUS = 3

# Camera Constants

CAM_HORIZONTAL_FOV = 89#92.7 # FOV angle, in degrees
CAM_RESOLUTION = 1280, 720

# Precomputed value

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

if CAM_HORIZONTAL_FOV is None:
    # Calibrate focal length using initial positions
    FOCAL_LENGTH = calibrate_focal_length(
        *ball_projected_pos, initial_z=INITIAL_Z, initial_dst=BALL_DST
    )
else:
    FOCAL_LENGTH = (CAM_RESOLUTION[0] / 2) / np.tan(CAM_HORIZONTAL_FOV / 2 * (np.pi / 180))
    
# Estimate actual ball radius if not ignored
ball_actual_radius = BALL_RADIUS
if not IGNORE_BALL_RADIUS and not WEIGHTED_PIXELS_ELLIPSE_CORRECTION:
    # The balls may have a slightly different radius than assumed
    ball_actual_radius = ball_projected_radius * INITIAL_Z / FOCAL_LENGTH

# Set up display and UI
width = frame_array.shape[0]
height = frame_array.shape[1]
screen = pg.display.set_mode((width, height))
root = Root(screen, padding=PADDING)
axis_widget = AxisWidget(
    root, x=np.array((1, 0, 0)), y=np.array((0, 1, 0)), z=np.array((0, 0, 0))
)
image_widget = ImageWidget(root, pixels=[], curr_pos=(0, 0))
checkboxes = Checkboxes(root, options = ['DEBUG BALLS'], checked = [DEBUG_BALLS], req_width=200, background=(255,255,255))

root.update_layout()
clock = pg.time.Clock()
points = []  # List of pen tip positions
paths = [[]]

# ----------------------
# Main Loop
# ----------------------
STATUS = "computing"
while STATUS != "quit":
    for event in pg.event.get():
        if event.type == pg.QUIT:
            STATUS = "quit"
        root.process_event(event)
        DEBUG_BALLS = checkboxes.checked[0]

    if STATUS == "computing":
        try:
            for i in range(SKIP_FRAMES):
                next(video)
            frame_array, aud_array = next(video)
        except StopIteration:
            paths[-1] = median_line_smoothing(paths[-1], 10)
            points = [i for sublist in paths for i in sublist]
            image_widget.set_data(points, None)
            save_pixels(points, OUTPUT_FILENAME)
            STATUS = "saved"
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

        if pen_down:
            # Compute 3D rays from camera to each ball
            if TANGENTIAL_ELLIPSE_CORRECTION:
                ball_tangential_points = get_tangential_points(
                    threshold_array, USE_LINE_MASK
                )
                ball_rays, distances = find_angle_bisectors(
                    ball_tangential_points[:, 0, :],
                    ball_tangential_points[:, 1, :],
                    width,
                    height,
                    FOCAL_LENGTH,
                    ball_actual_radius,
                )
            elif WEIGHTED_PIXELS_ELLIPSE_CORRECTION:
                ball_rays, ball_fractional_area = get_all_balls_weighted(
                    threshold_array, FOCAL_LENGTH
                )
            else:
                ball_projected_pos, ball_projected_radius = get_all_balls(
                    threshold_array
                )
                ball_rays = get_rays(ball_projected_pos, width, height, FOCAL_LENGTH)

            if IGNORE_BALL_RADIUS:
                # Use geometric constraint to solve for scale factors
                scale_factors = compute_ts(*ball_rays, BALL_DST)
            elif TANGENTIAL_ELLIPSE_CORRECTION:
                scale_factors = distances
            elif WEIGHTED_PIXELS_ELLIPSE_CORRECTION:
                scale_factors = distance_from_area(ball_fractional_area, BALL_RADIUS)
            else:
                # Use projected and actual radii to solve for scale factors
                z = ball_actual_radius / ball_projected_radius * FOCAL_LENGTH
                scale_factors = -z / ball_rays[:, 2]
            scale_factors = scale_factors * DST_CALIB_CONSTANT
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
            image_widget.set_data(points, (pen_tip[0], pen_tip[2]))

            if IGNORE_AUDIO:
                if pen_tip[1] >= -PEN_LENGTH + PEN_THRESHOLD:
                    pen_down = False

        if pen_down:
            points.append((pen_tip[0], pen_tip[2]))
            paths[-1].append((pen_tip[0], pen_tip[2]))
        else:
            if len(paths[-1]) > 0:
                paths[-1] = median_line_smoothing(paths[-1], SMOOTHING_CONSTANT)
                points = [i for sublist in paths for i in sublist]
                paths.append([])
                image_widget.set_data(points, None)

    # ----------------------
    # Drawing
    # ----------------------
    if DEBUG_BALLS:
        multiplier = 100
    else:
        multiplier = 255
    display_array = (threshold_array * multiplier).astype(np.uint8)
    pg.surfarray.blit_array(screen, display_array)
    if pen_down:
        if TANGENTIAL_ELLIPSE_CORRECTION:
            for j in ball_tangential_points:
                for k in j:
                    pg.draw.circle(screen, (255, 255, 255), k, 10, 2)
                if USE_LINE_MASK:
                    pg.draw.line(screen, (255,255,255), (width//2, height//2), k)
                
        elif not WEIGHTED_PIXELS_ELLIPSE_CORRECTION:
            for j in range(3):
                pg.draw.circle(screen, (255, 255, 255), ball_projected_pos[j], 10)
                pg.draw.circle(
                    screen,
                    (255, 255, 255),
                    ball_projected_pos[j],
                    ball_projected_radius[j],
                    5,
                )
                
        if DEBUG_BALLS:
            for j in range(3):
                arr = np.not_equal(
                        render_ball(ball_rays[j], BALL_RADIUS, scale_factors[j], width, height, FOCAL_LENGTH),
                        threshold_array[:, :, j]
                        ) * 255
                surface = pg.surfarray.make_surface(arr)
                screen.blit(surface, (0,0), special_flags=pg.BLEND_RGB_ADD)
                
        pg.draw.line(screen, (255, 255, 0), (width//2, 0),
                                              (width//2, height))
        pg.draw.line(screen, (255, 255, 0), (width, height//2),
                                              (0, height//2))
                
    # Render UI widgets
    root.render()
    pg.display.flip()
    clock.tick(FPS)

    pg.display.set_caption(f"FPS: {clock.get_fps():.2f} | Status: {STATUS}")

pg.quit()
