import numpy as np
import cv2

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

#Only cache 1 shape, to avoid memory issues
DISTANCE_CACHE = None

def get_tangential_points(threshold_array: np.ndarray, use_line_mask: bool = True) -> np.ndarray:
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
        if use_line_mask:
            # Create a mask for the line through the center and the ball
            line_mask = create_line_mask(threshold_array.shape[0], threshold_array.shape[1],
                                  principal_point, (ball_px[0].mean(), ball_px[1].mean()))
            ball_px = np.nonzero(np.logical_and(threshold_array[:, :, i], line_mask))
        if ball_px[0].size == 0:
            continue

        dists = D[ball_px[0], ball_px[1]]   # 1D array, len = # of nonzero pixels in channel i

        idx_near  = np.argmin(dists)
        idx_far   = np.argmax(dists)

        tangential_points[i, 0] = ball_px[0][idx_near], ball_px[1][idx_near]
        tangential_points[i, 1] = ball_px[0][idx_far],  ball_px[1][idx_far]
    return tangential_points

def create_line_mask(w, h, p1, p2):
    """
    Create a mask for the infinite line through p1 and p2,
    clipped to an image of size (w,h), returned as shape (w,h),
    with one-pixel continuity.
    """
    x0, y0 = p1
    x1, y1 = p2
    dx, dy = x1 - x0, y1 - y0

    mask = np.zeros((w, h), dtype=bool)

    # Vertical line
    if dx == 0:
        if 0 <= x0 < w:
            mask[x0, :] = True
        return mask

    # Horizontal line
    if dy == 0:
        if 0 <= y0 < h:
            mask[:, y0] = True
        return mask

    slope = dy / dx

    if abs(slope) <= 1:
        xs = np.arange(w)
        ys = y0 + slope * (xs - x0)
        ys_round = np.round(ys).astype(int)
        valid = (ys_round >= 0) & (ys_round < h)
        xs_valid = xs[valid]
        ys_valid = ys_round[valid]
        mask[xs_valid, ys_valid] = True

    else:
        inv_slope = dx / dy
        ys = np.arange(h)
        xs = x0 + inv_slope * (ys - y0)
        xs_round = np.round(xs).astype(int)
        valid = (xs_round >= 0) & (xs_round < w)
        xs_valid = xs_round[valid]
        ys_valid = ys[valid]
        mask[xs_valid, ys_valid] = True

    return mask

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

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    # Define image dimensions and two points
    w, h = 120, 80
    p1 = (20, 10)
    p2 = (100, 70)

    # Generate the mask
    mask_wh = create_line_mask(w, h, p1, p2)

    # Inspect the shape
    print("mask shape (w, h):", mask_wh.shape)  # -> (120, 80)

    # Visualize: transpose back to (h,w) for imshow
    plt.figure(figsize=(6,4))
    plt.imshow(mask_wh.T, cmap="gray", origin="lower")
    plt.scatter([p1[0], p2[0]], [p1[1], p2[1]], c="red", zorder=2)
    plt.title("Infinite Line Mask (visualized)")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.show()