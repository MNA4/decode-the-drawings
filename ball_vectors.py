"""
ball_vectors.py
Mathematical utilities for 3D geometry, camera calibration, and orientation estimation for the Decode the Drawings project.
"""

import numpy as np

def distance(v: np.ndarray) -> float:
    """
    Calculate the Euclidean distance (L2 norm) of a vector.
    Args:
        v (numpy.ndarray): The input vector.
    Returns:
        float: The Euclidean distance of the vector.
    """
    return np.linalg.norm(v)


def normalize(v: np.ndarray) -> np.ndarray:
    """
    Normalize a vector to unit length.
    Args:
        v (numpy.ndarray): The input vector.
    Returns:
        numpy.ndarray: The normalized vector.
    """
    return v / distance(v)


def calibrate_focal_length(*points: np.ndarray, initial_z: float, initial_dst: float) -> float:
    """
    Calibrates the focal length of the camera based on the positions of the balls.
    Args:
        points (numpy.ndarray): The 2D projected coordinates of the balls.
        initial_z (float): The initial z distance from the camera to the balls in cm.
        initial_dst (float): The initial distance between the balls in cm.
    Returns:
        float: The computed focal length.
    """
    # Calculate average distance between points (assumes 3 points)
    projected_length = 0
    for i in range(-1, len(points) - 1):
        projected_length += distance(points[i] - points[i + 1])
    projected_length /= 3
    # Pinhole Camera Model:
    # projected_length = f × actual_length ÷ z
    # focal_length f = projected_length × z ÷ actual_length
    return initial_z / initial_dst * projected_length


def get_rays(projected_points: np.ndarray, vw: int, vh: int, f: float) -> np.ndarray:
    """
    Calculate the rays from the camera to the projected points in 3D space.
    Args:
        projected_points (numpy.ndarray): The 2D coordinates of the projected points.
        vw (int): The width of the viewport.
        vh (int): The height of the viewport.
        f (float): The focal length of the camera.
    Returns:
        numpy.ndarray: An array of shape (N, 3) containing the rays in 3D space,
                      where N is the number of projected points.
    """
    # Pinhole Camera Model:
    # ray = (projected_x - viewport_width / 2, -(projected_y - viewport_height / 2), -f)
    # The Y axis is flipped for a right-handed coordinate system.
    # The Z axis is flipped, since the camera is pointing onto the scene.
    projected_points = np.asarray(projected_points)
    rays = np.empty((projected_points.shape[0], 3))
    rays[:, 0] = projected_points[:, 0] - vw / 2
    rays[:, 1] = - (projected_points[:, 1] - vh / 2)
    rays[:, 2] = -f
    # Normalize the rays to unit length
    rays = rays / np.linalg.norm(rays, axis=1, keepdims=True)
    return rays


def compute_ts(r1: np.ndarray, r2: np.ndarray, r3: np.ndarray, side: float) -> tuple:
    """
    Compute the scale factors t1, t2, t3 such that P_i = t_i * r_i
    form an equilateral triangle of side length `side`, given
    unit direction vectors r1, r2, r3 (3-element arrays).
    Args:
        r1, r2, r3 (np.ndarray): Unit direction vectors (rays) from the camera origin.
        side (float): The desired length of each side of the equilateral triangle.
    Returns:
        numpy.ndarray: An array of shape (3,) containing the scale factors t1, t2, t3.
    """
    # Compute dot products
    c12 = np.dot(r1, r2)
    c23 = np.dot(r2, r3)
    c13 = np.dot(r1, r3)
    u12, u23, u13 = 1 - c12, 1 - c23, 1 - c13
    sqrt_d = np.sqrt(2.0 * u12 * u23 * u13)
    return side * np.array((u23, u13, u12)) / sqrt_d


def get_orientation(b1: np.ndarray, b2: np.ndarray, b3: np.ndarray) -> tuple:
    """
    Calculate the orientation of the triangle formed by three points in 3D space.
    Args:
        b1, b2, b3 (numpy.ndarray): The 3D coordinates of the points.
    Returns:
        tuple: A tuple containing the x, y, z axes of the triangle's orientation.
    """
    x_axis = normalize(b2 - b3)
    z_axis = normalize(np.cross(x_axis, b1 - b3))
    y_axis = normalize(np.cross(z_axis, x_axis))
    return x_axis, y_axis, z_axis


def orient_pos(pos: np.ndarray,
               x_axis: np.ndarray,
               y_axis: np.ndarray,
               z_axis: np.ndarray) -> np.ndarray:
    """
    Orient a position vector to the triangle's orientation defined by its axes.
    Args:
        pos (numpy.ndarray): The 3D position vector to orient.
        x_axis (numpy.ndarray): The x-axis of the triangle's orientation.
        y_axis (numpy.ndarray): The y-axis of the triangle's orientation.
        z_axis (numpy.ndarray): The z-axis of the triangle's orientation.
    Returns:
        numpy.ndarray: The oriented position vector.
    """
    return np.array([
        np.dot(pos, x_axis),
        np.dot(pos, y_axis),
        np.dot(pos, z_axis),
    ])
