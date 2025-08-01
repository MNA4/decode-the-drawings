import numpy as np
from vectors import (
    area_fraction_image,
    get_frame_rays,
    normalize
)

def get_all_balls(threshold_array: np.ndarray) -> tuple:
    """
    Calculate the positions and radii of all balls in the frame.
    Args:
        threshold_array (numpy.ndarray): The video frame as a 3D numpy array (width, height, channels).
    Returns:
        tuple: A tuple containing:
            - pos (numpy.ndarray): An array of shape (3, 2) containing the average positions of the balls.
            - radius (numpy.ndarray): An array of shape (3,) containing the calculated radii of the balls.
    """
    pos = np.empty([3, 2])
    radius = np.empty([3])
    for i in range(3):
        ball_px = np.nonzero(threshold_array[:, :, i])
        pos[i] = (ball_px[0].mean(), ball_px[1].mean())

        # area = π × radius²
        # radius = √(area ÷ π)

        radius[i] = np.sqrt(ball_px[0].shape[0] / np.pi)
    return pos, radius

RAYS_CACHE = None
PIXEL_AREA_CACHE = None
PIXEL_WEIGHT_CACHE = None
F_CACHE = None

def get_all_balls_weighted(threshold_array: np.ndarray, f: float) -> tuple:
    """
    Calculate the weighted positions and radii of all balls in the frame,
    using per-pixel solid-angle fractions as weights.
    Args:
        threshold_array (numpy.ndarray): shape (w, h, 3), boolean or 0/1 mask per color.
        f (float): focal length, same units as area_fraction_image expects.
    Returns:
        pos (np.ndarray): shape (3,2) of each ball's weighted centroid (x,y,z).
        radius (np.ndarray): shape (3,), the ball's fractional area on the unit sphere.
    """
    global PIXEL_AREA_CACHE, PIXEL_WEIGHT_CACHE, F_CACHE
    w, h = threshold_array.shape[:2]
    cx = w / 2  # or your actual principal-point
    cy = h / 2
    # lazily build the area‐fraction cache if needed
    if PIXEL_AREA_CACHE is None or PIXEL_AREA_CACHE.shape != (w, h) or F_CACHE != f:
        x, y = np.indices(threshold_array.shape[:2])
        PIXEL_AREA_CACHE = area_fraction_image(w, h, cx, cy, f)
        F_CACHE = f
        ray_length = np.sqrt((x - cx)**2 + (y - cy)**2 + f**2)
        PIXEL_WEIGHT_CACHE = PIXEL_AREA_CACHE / ray_length

    pos = np.zeros((3, 2), dtype=float)
    A = np.zeros(3, dtype=float)

    for i in range(3):
        xs, ys = np.nonzero(threshold_array[:, :, i])
        weight_area = PIXEL_AREA_CACHE[xs,ys]
        weight_pixel = PIXEL_WEIGHT_CACHE[xs,ys]
        
        pos[i, 0] = np.average(xs, weights = weight_pixel)
        pos[i, 1] = np.average(ys, weights = weight_pixel)
        
        total = weight_area.sum()
        A[i] = total
        
    return pos, A

def render_ball(center, radius, distance, w, h, f):
    "Used for debugging & finding errors in the program."
    global F_CACHE, RAYS_CACHE
    if RAYS_CACHE is None or RAYS_CACHE.shape != (w, h) or F_CACHE != f:
        RAYS_CACHE = get_frame_rays(w, h, f)
        F_CACHE = f
    cos_ = np.sqrt(1-(radius/distance)**2)
    dot_ = np.sum(RAYS_CACHE * center, axis = 2) - cos_
    return dot_ > 0

# Only cache 1 shape, to avoid memory issues
DISTANCE_CACHE = None


def get_tangential_points(
    threshold_array: np.ndarray, use_line_mask: bool = True
) -> np.ndarray:
    """
    Get the tangential points of the balls in the frame.
    Args:
        threshold_array (numpy.ndarray): The video frame as a 3D numpy array (width, height, channels).
    Returns:
        tangential_points : (3, 2, 2) int
            For each channel i=0..2, two (row, col) points:
            [i,0] = the 'inner' tangential point
            [i,1] = the 'outer' tangential point
    """
    global DISTANCE_CACHE

    tangential_points = np.empty([3, 2, 2])  # 3 balls, 2 points each
    principal_point = np.array(threshold_array.shape[:2]) // 2

    if DISTANCE_CACHE is None or DISTANCE_CACHE.shape != threshold_array.shape[:2]:
        x, y = np.indices(threshold_array.shape[:2])
        DISTANCE_CACHE = (x - principal_point[0]) ** 2 + (y - principal_point[1]) ** 2

    D = DISTANCE_CACHE
    for i in range(3):
        ball_px = np.nonzero(threshold_array[:, :, i])
        if use_line_mask:
            ball_px = filter_line(
                (ball_px[0].mean(), ball_px[1].mean()), principal_point, ball_px
            )
        if ball_px[0].size == 0:
            continue

        dists = D[
            ball_px[0], ball_px[1]
        ]  # 1D array, len = # of nonzero pixels in channel i

        idx_near = np.argmin(dists)
        idx_far = np.argmax(dists)

        tangential_points[i, 0] = ball_px[0][idx_near], ball_px[1][idx_near]
        tangential_points[i, 1] = ball_px[0][idx_far], ball_px[1][idx_far]
    return tangential_points


def filter_line(p1, p2, nonzeros):
    """
    Filter the nonzero pixels to only include those that are on the infinite line defined by p1 and p2.
    Args:
        p1: First point (x, y).
        p2: Second point (x, y).
        nonzeros: Nonzero pixel coordinates.
    Returns:
        Filtered nonzero pixel coordinates that are on the infinite line.
    """
    x0, y0 = p1
    x1, y1 = p2
    dx, dy = x1 - x0, y1 - y0
    if dx == 0 and dy == 0:
        return nonzeros  # p1 and p2 are the same point, return all nonzeros
    elif dy <= dx:
        slope = dy / dx
        ys = y0 + slope * (nonzeros[0] - x0)
        mask = np.round(ys) == nonzeros[1]
    else:
        inv_slope = dx / dy
        xs = x0 + inv_slope * (nonzeros[1] - y0)
        mask = np.round(xs) == nonzeros[0]
    return nonzeros[0][mask], nonzeros[1][mask]


def threshold(frame: np.ndarray,
              inv_saturation_threshold: float,
              lightness_threshold: float) -> np.ndarray:
    """
    Apply a threshold to the frame array to create a binary mask.
    Args:
        frame (np.ndarray): The video frame as a 3D array (H, W, C).
        inv_saturation_threshold (float): Inverse of the saturation threshold (0–1).
        lightness_threshold (float): Lightness threshold (0–255).
    Returns:
        np.ndarray: A boolean mask of shape (H, W, C).
    """
    # 1) Compute per-pixel average (float32)
    avg = frame.sum(axis=2, dtype=np.float32) * (1.0 / 3.0)

    # 2) Scale by inv_saturation_threshold and enforce the lightness floor
    #    We get a float32 threshold map, then cast once to frame.dtype
    per_pixel_thresh = np.maximum(avg * inv_saturation_threshold,
                                  lightness_threshold).astype(frame.dtype)

    # 3) Single vectorized comparison across channels
    #    Broadcasting per_pixel_thresh from (H, W) → (H, W, 1)
    return frame > per_pixel_thresh[:, :, None]