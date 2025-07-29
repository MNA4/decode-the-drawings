"""
ball_vectors.py
Mathematical utilities for 3D geometry, camera calibration, and orientation estimation for the Decode the Drawings project.
"""

import numpy as np

def distance(v: np.ndarray, axis = None) -> float:
    """
    Calculate the Euclidean distance (L2 norm) of a vector.
    Args:
        v (numpy.ndarray): The input vector.
    Returns:
        float: The Euclidean distance of the vector.
    """
    return np.linalg.norm(v, axis = axis, keepdims=True)


def normalize(v: np.ndarray, axis = None) -> np.ndarray:
    """
    Normalize a vector to unit length.
    Args:
        v (numpy.ndarray): The input vector.
    Returns:
        numpy.ndarray: The normalized vector.
    """
    return v / distance(v, axis = axis)


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
    return normalize(rays, axis=1)


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

def find_angle_bisectors(p1s: np.ndarray, p2s: np.ndarray, vw: int, vh: int, f: float, ball_radius: int) -> tuple:
    """
    find the angle bisectors between rays p1s and p2s.
    Args:
        p1s, p2s (numpy.ndarray): where rays that point to p1s and p2s are tangential to the balls.
        vw (int): The width of the viewport.
        vh (int): The height of the viewport.
        f (float): The focal length of the camera.
    Returns:
        numpy.ndarray: An array of shape (N, 3) containing the rays in 3D space,
                      where N is the number of balls.
                      
        numpy.ndarray: An array of shape (N,) containing the lengths of the bisectors.
    """
    r1s = get_rays(p1s, vw, vh, f)
    r2s = get_rays(p2s, vw, vh, f)
    c = normalize(np.sum([r1s, r2s], axis=0), axis=1)  # Average the rays to find angle bisectors
    dot_products = np.sum(c * r1s, axis=1)
    sin_ = np.sqrt(1 - dot_products ** 2)
    L = ball_radius / sin_  # Length of the bisectors
    return c, L

def distance_from_area(A: float, R: float) -> float:
    """
    A    : fractional area 
    R    : actual sphere radius in same linear units as D
    returns D: distance from pinhole to sphere center
    """
    return R / np.sqrt(1-(1-2*A)**2)

def area_fraction_image(
    w: int, h: int, cx: float, cy: float, f: float, dx: float = 1.0, dy: float = 1.0
) -> np.ndarray:
    """
    Compute, for every pixel (x=0…w-1, y=0…h-1), the fraction of the full 4π steradians
    subtended by a pixel of size dxdy centered at that (x,y), using numpy.indices.

    Returns:
        A numpy array of shape (w, h), where element [i, j] is the fraction for pixel
        center at (x=i, y=j).
    """
    # Generate coordinate grids (w, h) with numpy.indices
    xm, ym = np.indices((w, h))  # shape (2, w, h)

    # ray's length
    l = np.sqrt((xm - cx) ** 2 + (ym - cy) ** 2 + f**2)

    # Differential solid angle for each pixel
    d_omega = f * (dx * dy) / l**3

    # Fraction of full sphere = dΩ / (4π)
    return d_omega / (4 * np.pi)
