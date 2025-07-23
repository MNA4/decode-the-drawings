import numpy as np

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
        pos[i] = np.mean(ball_px[0]), np.mean(ball_px[1])

        # area = π × radius²
        # radius = √(area ÷ π)

        radius[i] = np.sqrt(ball_px[0].shape[0] / np.pi)
    return pos, radius

#Only cache 1 shape, to avoid memory issues
DISTANCE_CACHE = None

def get_tangential_points(threshold_array: np.ndarray) -> np.ndarray:
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
        DISTANCE_CACHE = np.empty(threshold_array.shape[:2], dtype=np.uint32)
        x,y = np.indices(threshold_array.shape[:2])
        DISTANCE_CACHE = (x - principal_point[0]) ** 2 + \
                         (y - principal_point[1]) ** 2

    D = DISTANCE_CACHE
    for i in range(3):
        ball_px = np.nonzero(threshold_array[:, :, i])
        if ball_px[0].size == 0:
            continue

        dists = D[ball_px[0], ball_px[1]]   # 1D array, len = # of nonzero pixels in channel i

        # 3) find which one is nearest / farthest
        idx_near  = np.argmin(dists)
        idx_far   = np.argmax(dists)

        # 4) convert those back into (row, col)
        y_near, x_near = ball_px[0][idx_near], ball_px[1][idx_near]
        y_far,  x_far  = ball_px[0][idx_far],  ball_px[1][idx_far]

        # 5) store them
        tangential_points[i, 0] = (y_near, x_near)
        tangential_points[i, 1] = (y_far,  x_far)
    return tangential_points


def threshold(frame_array: np.ndarray, inv_saturation_threshold: float, lightness_threshold: float) -> np.ndarray:
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
    avg = np.sum(frame_array, axis=2) * 0.3333
    return np.logical_and(
           frame_array > (avg * inv_saturation_threshold)[:, :, np.newaxis],
           frame_array > lightness_threshold)
