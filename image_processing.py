import numpy as np
def get_all_balls(frame_array: np.ndarray, inv_threshold: float) -> tuple:
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
    sum_ = np.sum(frame_array, axis=2) * inv_threshold * 0.3333
    for i in range(3):
        threshold_array = frame_array[:, :, i] > sum_

        ball_px = np.argwhere(threshold_array)
        pos[i] = np.average(ball_px, axis=0)

        # area = π × radius²
        # radius = √(area ÷ π)

        radius[i] = np.sqrt(ball_px.shape[0] / np.pi)
    return pos, radius