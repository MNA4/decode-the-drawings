import numpy as np
import pygame as pg
from widgets import Root, ImageWidget, AxisWidget
from media import video_generator, audio_intensity
from image_processing import get_all_balls
from ball_vectors import calibrate_focal_length, get_rays, compute_ts, get_orientation, orient_pos

VIDEO_PATH = "3.mp4"
OUTPUT_FILENAME = "pixels.txt"
PADDING = 10
FPS = 60
PIXEL_THRESHOLD = 80  # in percent
# PEN_THRESHOLD = 1
AUDIO_THRESHOLD = 0.0013
INITIAL_Z = 18
PEN_LENGTH = 18
INITIAL_DST = 9

INV_THRESHOLD = 100 / (PIXEL_THRESHOLD * 3)

video = video_generator(VIDEO_PATH)
frame_array, _ = next(video)
ball_projected_pos, ball_projected_radius = get_all_balls(frame_array, INV_THRESHOLD)
focal_length = calibrate_focal_length(*ball_projected_pos,
                                       initial_z=INITIAL_Z,
                                       initial_dst=INITIAL_DST)

# Pinhole Camera Model:
# projected_radius = f × actual_radius ÷ z
# We can rearrange this to find the actual radius:
# actual_radius = projected_radius × z ÷ f

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
            frame_array, INV_THRESHOLD
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
        x_axis, y_axis, z_axis = get_orientation(
            ball_actual_pos[0], ball_actual_pos[1], ball_actual_pos[2]
        )
        non_oriented_cam_pos = -np.average(ball_actual_pos, axis=0)
        non_oriented_pen_tip = non_oriented_cam_pos - (0, PEN_LENGTH, 0)
        
        # Compute pen_tip in the triangle's local coordinate system
        pen_tip = orient_pos(non_oriented_pen_tip, x_axis, y_axis, z_axis)
        aud_intensity = audio_intensity(aud_array)
        if aud_intensity > AUDIO_THRESHOLD:  # pen_tip[1]<-PEN_LENGTH+PEN_THRESHOLD:
            pixels.append((pen_tip[0], pen_tip[2]))

        axis_widget.set_axes(x_axis, y_axis, z_axis)
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
