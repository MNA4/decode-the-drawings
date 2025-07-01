import numpy as np
import pygame as pg
import av
from widgets import Root, ImageWidget, AxisWidget

VIDEO_PATH = "2.mp4"
OUTPUT_FILENAME = "pixels.txt"
PADDING = 10
FPS = 60
PIXEL_THRESHOLD = 80  # in percent
# PEN_THRESHOLD = 1
AUDIO_THRESHOLD = 0.0013
INITIAL_Z = 18
PEN_LENGTH = 18
INITIAL_DST = 9


def video_generator(filename):
    """Generator that yields video frames and audio samples from a video file.
    Args:
        filename (str): Path to the video file.
    Yields:
        tuple: A tuple containing a video frame (as a numpy array)
               and an audio sample (as a numpy array).
    """
    container = av.open(filename)
    vid = None
    aud = None
    prev_aud = np.empty((1,))
    for frame in container.decode(video=0, audio=0):
        if isinstance(frame, av.audio.frame.AudioFrame):
            if aud is None:
                aud = frame.to_ndarray()[0]
            else:
                aud = np.concatenate((aud, frame.to_ndarray()[0]))
            continue

        elif isinstance(frame, av.video.frame.VideoFrame):
            vid = np.swapaxes(frame.to_rgb().to_ndarray(format="rgb24"), 0, 1)
            if aud is None:
                yield vid, prev_aud
            else:
                yield vid, aud
                prev_aud = aud.copy()
            aud = None
    container.close()


def get_all_balls(frame_array, inv_threshold):
    """
    Calculate the positions and radii of all balls in the frame.
    Args:
        frame_array (numpy.ndarray): The video frame as a 3D numpy array (width, height, channels).
        inv_threshold (float): The inverse of the threshold for detecting ball pixels.
    Returns:
        tuple: A tuple containing:
            - pos (numpy.ndarray): An array of shape (3, 2) containing the average positions of the balls.
            - radius (numpy.ndarray): An array of shape (3,) containing the calculated radii of the balls.
    """
    pos = np.empty([3, 2])
    radius = np.empty([3])
    sum_ = np.sum(frame_array, axis=2) * inv_threshold
    for i in range(3):
        threshold_array = frame_array[:, :, i] > sum_

        ball_px = np.argwhere(threshold_array)
        pos[i] = np.average(ball_px, axis=0)

        # area = π × radius²
        # radius = √(area ÷ π)

        radius[i] = np.sqrt(ball_px.shape[0] / np.pi)
    return pos, radius


def distance(v):
    """Calculate the Euclidean distance of a vector.
    Args:
        v (numpy.ndarray): The input vector.
    Returns:
        float: The Euclidean distance of the vector.
    """
    return np.linalg.norm(v)


def normalize(v):
    """Normalize a vector to unit length.
    Args:
        v (numpy.ndarray): The input vector.
    Returns:
        numpy.ndarray: The normalized vector.
    """
    return v / distance(v)


def calibrate_focal_length(*points):
    """
    Calibrates the focal length of the camera based on the positions of the balls.
    Args:
        points (numpy.ndarray): The 3D coordinates of the balls.
    Returns:
        float: The computed focal length.
    """
    # calculate average distance between points
    projected_length = 0
    for i in range(-1, len(points) - 1):
        projected_length += distance(points[i] - points[i + 1])

    projected_length /= 3

    #    Pinhole Camera Model:
    #
    #    projected_length = f × actual_length ÷ z
    #
    #    We are given that:
    #        actual_length = 9cm
    #        z = 18cm

    #    focal_length f = projected_length × z ÷ actual_length

    return INITIAL_Z / INITIAL_DST * projected_length


def get_rays(projected_points, vw, vh, f):
    """
    Pinhole Camera Model:

    ray = (projected_x - viewport_width ÷ 2, projected_y - viewport_height ÷ 2, focal_length)

    In this case i'm flipping the y & z axis for a right-handed coordinate system.
    """
    projected_points = np.asarray(projected_points)
    # Subtract center, flip y, set z to -f
    rays = np.empty((projected_points.shape[0], 3))
    rays[:, 0] = projected_points[:, 0] - vw / 2
    rays[:, 1] = - (projected_points[:, 1] - vh / 2)
    rays[:, 2] = -f
    # Normalize the rays to unit length
    rays = rays / np.linalg.norm(rays, axis=1, keepdims=True)
    return rays


def compute_ts(r1, r2, r3, side):
    """
    Compute the scale factors t1, t2, t3 such that P_i = t_i * r_i
    form an equilateral triangle of side length `side`, given
    unit direction vectors r1, r2, r3 (3-element arrays).

    Args:
    - r1, r2, r3: array-like, shape (3,)
        Unit direction vectors (rays) from the camera origin.
    - side: float
        Desired side length of the reconstructed triangle.

    Returns:
    - t1, t2, t3: floats
        Scaling factors along each ray to the triangle vertices.
    """

    # Compute dot products
    c12 = np.dot(r1, r2)
    c23 = np.dot(r2, r3)
    c13 = np.dot(r1, r3)

    u12, u23, u13 = 1 - c12, 1 - c23, 1 - c13

    sqrt_d = np.sqrt(2.0 * u12 * u23 * u13)

    # Scale factors simplified (avoids multiple sqrt calls)
    t1 = side * u23 / sqrt_d
    t2 = side * u13 / sqrt_d
    t3 = side * u12 / sqrt_d

    return t1, t2, t3


inv_threshold = 100 / (PIXEL_THRESHOLD * 3)

video = video_generator(VIDEO_PATH)
frame_array, _ = next(video)
ball_projected_pos, ball_projected_radius = get_all_balls(frame_array, inv_threshold)
focal_length = calibrate_focal_length(*ball_projected_pos)


"""
    Pinhole Camera Model:
    
    projected_length = f × actual_length ÷ z
    actual_length = projected_length × z ÷ f
"""
ball_actual_radius = ball_projected_radius * INITIAL_Z / focal_length

width = frame_array.shape[0]
height = frame_array.shape[1]

screen = pg.display.set_mode((width, height))

root = Root(screen)
axis_widget = AxisWidget(root, x=None, y=None, z=None)
image_widget = ImageWidget(root, pixels=[], curr_pos=(0, 0))
root.update_layout()
clock = pg.time.Clock()

pixels = []

stopped = False
running = True
while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
        root.process_event(event)

    if not stopped:
        try:
            frame_array, aud_array = next(video)
        except StopIteration:
            with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
                f.writelines(f"{i[0]} {i[1]}\n" for i in pixels)
            stopped = True
            print("done!")
            continue

        ball_projected_pos, ball_projected_radius = get_all_balls(
            frame_array, inv_threshold
        )

        ball_actual_pos = np.empty([ball_projected_pos.shape[0], 3])
        ball_rays = get_rays(ball_projected_pos, width, height, focal_length)
        # calculate the scale factors t1, t2, t3 such that P_i = t_i * r_i
        # t1, t2, t3 = compute_ts(ball_rays[0], ball_rays[1], ball_rays[2], INITIAL_DST)
        # # calculate the actual positions of the balls
        # ball_actual_pos[0] = t1 * ball_rays[0]
        # ball_actual_pos[1] = t2 * ball_rays[1]
        # ball_actual_pos[2] = t3 * ball_rays[2]

        z = ball_actual_radius / ball_projected_radius * focal_length
        scale_factors = -z / ball_rays[:, 2]
        ball_actual_pos = ball_rays * scale_factors[:, np.newaxis]

        # the triangle's orientation, from the camera's point of view
        # x_axis = normalize(ball_actual_pos[1] - ball_actual_pos[2])
        # y_axis = normalize(
        #     ball_actual_pos[0] - (ball_actual_pos[1] + ball_actual_pos[2]) / 2
        # )
        # z_axis = normalize(np.cross(x_axis, y_axis))
        x_axis = normalize(ball_actual_pos[1] - ball_actual_pos[2])
        z_axis = normalize(np.cross(x_axis, ball_actual_pos[0] - ball_actual_pos[2]))
        y_axis = -normalize(np.cross(x_axis, z_axis))
        non_oriented_cam_pos = -np.average(ball_actual_pos, axis=0)
        non_oriented_pen_tip = non_oriented_cam_pos - y_axis * PEN_LENGTH
        
        # Compute pen_tip in the triangle's local coordinate system
        pen_tip = np.array(
            (
            np.dot(non_oriented_pen_tip, x_axis),
            np.dot(non_oriented_pen_tip, y_axis),
            np.dot(non_oriented_pen_tip, z_axis),
            )
        )
        aud_intensity = np.sqrt(np.mean(aud_array**2))
        if aud_intensity > AUDIO_THRESHOLD:  # pen_tip[1]<-PEN_LENGTH+PEN_THRESHOLD:
            pixels.append((pen_tip[0], pen_tip[2]))

        axis_widget.set_axes(
            x_axis * (1, -1, 1),
            y_axis * (1, -1, 1),
            z_axis * (1, -1, 1)
        )
        image_widget.set_data(pixels, (pen_tip[0], pen_tip[2]))

    screen.blit(pg.surfarray.make_surface(frame_array), (0, 0))

    for j in range(3):
        pg.draw.circle(screen, (255, 255, 255), ball_projected_pos[j], 10)
        pg.draw.circle(
            screen, (255, 255, 255), ball_projected_pos[j], ball_projected_radius[j], 5
        )
        # Draw triangle connecting the three balls
    pts = [tuple(ball_projected_pos[i]) for i in range(3)]
    pg.draw.polygon(screen, (255, 255, 255), pts, 2)

    root.render()
    pg.display.flip()
    clock.tick(FPS)
    pg.display.set_caption(f"FPS: {clock.get_fps()}")

pg.quit()
