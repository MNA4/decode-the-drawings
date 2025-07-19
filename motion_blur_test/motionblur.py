import numpy as np
import matplotlib.pyplot as plt

RADIUS = 100
SAMPLES = 100
INITIAL_POS = (100, 200)  # Initial position of the circle
X_SPEED = 100  # Horizontal speed of the circle (pixels per second)
Y_SPEED = 0  # Vertical speed of the circle (pixels per second)
width, height = 400, 400  # Set the dimensions of the window

def draw_circle(t0, t1, w, h) -> np.ndarray:
    """
    Photograph a circle, which moves in a straight line from its initial position
    Args:
        t0: Start time.
        t1: End time.
        w: Width of the window.
        h: Height of the window.
    Returns:
        Photo of the circle at time t0 ~ t1.
    """
    t = np.random.random((SAMPLES, w, h)) * (t1 - t0) + t0
    _, x, y = np.mgrid[0:t.shape[0], 0:t.shape[1], 0:t.shape[2]]
    circle_x = INITIAL_POS[0] + t * X_SPEED
    circle_y = INITIAL_POS[1] + t * Y_SPEED

    return np.mean((circle_x - x)**2 + (circle_y - y)**2 <= RADIUS**2, axis=0)

image = np.transpose(draw_circle(0, 1, width, height))
image2 = np.transpose(draw_circle(1, 2, width, height))
image3 = np.transpose(draw_circle(1, 1, width, height))

fig, axs = plt.subplots(2, 2)
axs[0, 0].imshow(image3)
axs[0, 0].set_title("Circle at t=1 (expected output)")

axs[0, 1].imshow(np.logical_and(image2>0, image>0))
axs[0, 1].set_title("Recovered image at t=1 (output)")

axs[1, 0].imshow(image)
axs[1, 0].set_title("Photo at t0=0, t1=1 (input)")

axs[1, 1].imshow(image2)
axs[1, 1].set_title("Photo at t0=1, t1=2 (input)")
plt.show()