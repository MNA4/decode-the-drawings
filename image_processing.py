import numpy as np
from vectors import area_fraction_image


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


PIXEL_AREA_CACHE = None
F_CACHE = None


def get_all_balls_weighted(threshold_array: np.ndarray, f: float) -> tuple:
    """
    Calculate the weighted positions and radii of all balls in the frame,
    using per-pixel solid-angle fractions as weights.
    Args:
        threshold_array (numpy.ndarray): shape (w, h, 3), boolean or 0/1 mask per color.
        f (float): focal length, same units as area_fraction_image expects.
    Returns:
        pos (np.ndarray): shape (3,2) of weighted centroids (x,y).
        radius (np.ndarray): shape (3,), the circle's apparent radii on the unit sphere.
    """
    global PIXEL_AREA_CACHE, F_CACHE
    w, h = threshold_array.shape[:2]
    cx = w / 2  # or your actual principal-point
    cy = h / 2
    # lazily build the area‐fraction cache if needed
    if PIXEL_AREA_CACHE is None or PIXEL_AREA_CACHE.shape != (w, h) or F_CACHE != f:
        PIXEL_AREA_CACHE = area_fraction_image(w, h, cx, cy, f)
        F_CACHE = f

    pos = np.zeros((3, 2), dtype=float)
    A = np.zeros(3, dtype=float)

    for i in range(3):
        xs, ys = np.nonzero(threshold_array[:, :, i])
        weights = PIXEL_AREA_CACHE[xs, ys]

        # weighted centroid using np.average
        pos[i, 0] = np.average(xs, weights=weights)
        pos[i, 1] = np.average(ys, weights=weights)

        # weighted area → radius on unit sphere
        A[i] = np.sum(weights)
    return pos, A


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


def threshold(
    frame_array: np.ndarray, inv_saturation_threshold: float, lightness_threshold: float
) -> np.ndarray:
    """
    Apply a threshold to the frame array to create a binary mask.
    Args:
        frame_array (numpy.ndarray): The video frame as a 3D numpy array (width, height, channels).
        inv_saturation_threshold (float): The inverse of the saturation threshold for detecting ball pixels.
                                          saturation threshold is in the range (0-1).
        lightness_threshold (float): The lightness threshold for detecting ball pixels. (0-255)
    Returns:
        numpy.ndarray: A 3D binary mask where pixels above the threshold are set to True.
    """
    avg = (
        np.sum(frame_array, axis=2, dtype=np.float32) * 0.3333
    )  # float32 faster, avoids overflow

    # Precompute scaled threshold
    sat_thresh = (avg * inv_saturation_threshold).astype(
        frame_array.dtype
    )  # same type as frame for fast comp

    # Vectorized threshold checks (no broadcasting temp arrays)
    above_sat = frame_array > sat_thresh[:, :, None]
    above_light = frame_array > lightness_threshold

    return np.logical_and(above_sat, above_light)
