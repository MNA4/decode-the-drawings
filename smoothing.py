import numpy as np

def median_line_smoothing(path, smoothness):
    """
    Smooth the given path, by calculating the median every `smoothness` points.
    Args:
        path: list containing points (px,py)
        smoothness: the desired smoothness.
    Returns:
        list containing the smoothed out path.
    """
    if len(path) == 0:
        return []
    if len(path) <= smoothness:
        return [np.median(path, axis=0)]

    new_path = []
    for i in range(len(path) - smoothness):
        new_path.append(np.median(path[i:i+smoothness], axis=0))
    return new_path