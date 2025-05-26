import numpy as np
import pygame as pg
import av

VIDEO_PATH = "3.mp4"
PADDING = 10
FPS = 60
PIXEL_THRESHOLD = 120
#PEN_THRESHOLD = 1
AUDIO_THRESHOLD = 0.0013
INITIAL_Z = 18
PEN_LENGTH = 18
INITIAL_DST = 9

def video_generator(filename):
    container = av.open(filename)
    vid = None
    aud = None
    prev_aud = np.zeros((1,))
    for frame in container.decode(video=0, audio=0):
        if isinstance(frame, av.audio.frame.AudioFrame):
            if aud is None:
                aud = frame.to_ndarray()[0]
            else:
                aud = np.concatenate((aud, frame.to_ndarray()[0]))
            continue
        
        elif isinstance(frame, av.video.frame.VideoFrame):
            vid = np.swapaxes(frame.to_rgb().to_ndarray(format='rgb24'), 0, 1)
            if aud is None:
                yield vid, prev_aud
            else:
                yield vid, aud
                prev_aud = aud.copy()
            aud = None
    container.close()

def get_all_balls(threshold_array):
    pos = np.zeros([threshold_array.shape[2], 2])
    radius = np.zeros([threshold_array.shape[2]])
    for i in range(threshold_array.shape[2]):
        ball_px = np.argwhere(threshold_array[:, :, i])
        pos[i]=np.average(ball_px, axis=0)
        
        # area = π × radius²
        # radius = √(area ÷ π)
        
        radius[i] = np.sqrt(ball_px.shape[0]/np.pi)
    return pos, radius

def distance(v):
    return np.linalg.norm(v)

def normalize(v):
    return v/distance(v)

def calibrate_focal_length(*points):
    
    #calculate average distance between points
    projected_length = 0
    for i in range(-1, len(points)-1):
        projected_length += distance(points[i] - points[i+1])

    projected_length /= 3
    
    #    Pinhole Camera Model:
    #    
    #    projected_length = f × actual_length ÷ z
    #
    #    We are given that:
    #        actual_length = 9cm
    #        z = 18cm

    #    focal_length f = projected_length × z ÷ actual_length
        
    return INITIAL_Z/INITIAL_DST*projected_length
    
def get_ray(px, py, vw, vh, f):
    '''
        Pinhole Camera Model:

        ray = (projected_x - viewport_width ÷ 2, projected_y - viewport_height ÷ 2, focal_length)
        
        In this case i'm flipping the y & z axis for a right-handed coordinate system.
    '''
    #rays = np.zeros((len(projected_points), 3))
    #centered_points = projected_points-(vw/2, vh/2)
    #rays[:, 0] = centered_points[:, 0]
    #rays[:, 1] = centered_points[:, 1]
    #rays[:, 2] = f
    return np.array((px-vw/2, vh/2-py, -f))

def draw_axis(screen, bbox, padding, x, y, z):
    projected_axis = np.array((1,-1))*([0, 0], x[0:2], y[0:2], z[0:2])
    bound = [*np.min(projected_axis, axis=0), *np.max(projected_axis, axis=0)]
    wh = bound[2]-bound[0], bound[3]-bound[1]
    scale = min(bbox.width-padding*2, bbox.height-padding*2)/max(wh)
    ui_center = bbox.center
    scaled_axis = [((i[0]-bound[0]-wh[0]/2)*scale + ui_center[0],
                    (i[1]-bound[1]-wh[1]/2)*scale + ui_center[1]) for i in projected_axis]
    
    pg.draw.rect(screen, (255,255,255), bbox)
    for i in range(3):
        pg.draw.line(screen, [255*(i==j) for j in range(3)], scaled_axis[0], scaled_axis[i+1], 5)
  
def draw_image(screen, bbox, padding, pixels, curr_pos):
    pg.draw.rect(screen, (255,255,255), bbox)
    bound = [*np.min(pixels+[curr_pos], axis=0), *np.max(pixels+[curr_pos], axis=0)]
    wh = np.array((bound[2]-bound[0],
                   bound[3]-bound[1]))
    
    scale = min(bbox.width-padding*2, bbox.height-padding*2)/max(max(wh),0.1)
    ui_center = bbox.center
    
    pg.draw.circle(screen, (0,0,0),
                  ((curr_pos[0]-bound[0]-wh[0]/2)*scale + ui_center[0],
                   (curr_pos[1]-bound[1]-wh[1]/2)*scale + ui_center[1]), 5, 1)

    if pixels:                       
        scaled_pixels = (np.array(pixels)-bound[0:2]-wh/2)*scale + ui_center
        
        for i in scaled_pixels:
            pg.draw.rect(screen, (0,0,0), (i, (1, 1)), 1)

def get_bboxes(screen, padding, w, h, n_of_widgets):
    sw, sh = screen.get_size()
    pos = [sw - w - padding, padding]

    rects = [pg.Rect(pos, (w,h))]
    for _ in range(1, n_of_widgets):
        pos[1] += h + padding
        if pos[1] + h + padding > sh:
            pos[1] = padding
            pos[0] -= h - padding

        rects.append(pg.Rect(pos, (w,h)))
        
    return rects

video = video_generator(VIDEO_PATH)

frame_array, _ = next(video)
threshold_array = frame_array>PIXEL_THRESHOLD

ball_projected_pos, ball_projected_radius = get_all_balls(threshold_array)

focal_length = calibrate_focal_length(*ball_projected_pos)


'''
    Pinhole Camera Model:
    
    projected_length = f × actual_length ÷ z
    actual_length = projected_length × z ÷ f
'''
ball_actual_radius = ball_projected_radius * INITIAL_Z / focal_length

width = frame_array.shape[0]
height = frame_array.shape[1]

screen = pg.display.set_mode((width, height))
axis_bbox, image_bbox = get_bboxes(screen, 10, 200, 250, 2)
clock = pg.time.Clock()

pixels = []

stopped = False
running = True
while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
            
    if not stopped:
        try:
            frame_array, aud_array = next(video)
        except StopIteration:
            f = open('pixels.txt', 'w')
            for i in pixels:
                f.write('%s %s\n' % i)
            f.close()
            stopped = True
            print('done!')
            continue
        
        threshold_array = frame_array>PIXEL_THRESHOLD
        
        ball_projected_pos, ball_projected_radius = get_all_balls(threshold_array)
        
        ball_actual_pos = np.zeros([ball_projected_pos.shape[0], 3])
        for i in range(ball_projected_pos.shape[0]):
            ray = get_ray(*ball_projected_pos[i], width, height, focal_length)

            # again here we use a Pinhole Camera Model to find z
            z = ball_actual_radius[i] / ball_projected_radius[i] * focal_length
            ball_actual_pos[i] = ray * -z/ray[2]

        # the triangle's orientation, from the camera's point of view
        x_axis = normalize(ball_actual_pos[1] - ball_actual_pos[2])
        z_axis = normalize(np.cross(x_axis, ball_actual_pos[0] - ball_actual_pos[2]))
        y_axis = -normalize(np.cross(x_axis, z_axis))

        non_oriented_cam_pos = - np.average(ball_actual_pos, axis = 0)
        
        # oriented camera pos
        cam_pos = np.array((
            np.dot(non_oriented_cam_pos, x_axis),
            np.dot(non_oriented_cam_pos, y_axis),
            np.dot(non_oriented_cam_pos, z_axis),
            ))

        pen_direction = y_axis * (1, -1, 1)
        pen_tip = cam_pos + pen_direction * PEN_LENGTH

        aud_intensity = np.sqrt(np.mean(aud_array**2))
        if aud_intensity > AUDIO_THRESHOLD:#pen_tip[1]<-PEN_LENGTH+PEN_THRESHOLD:
            pixels.append((pen_tip[0], pen_tip[2]))
            
        display_array = threshold_array*200
    
    screen.blit(pg.surfarray.make_surface(frame_array), (0,0))
        
    for j in range(3):
        pg.draw.circle(screen, (255,255,255), ball_projected_pos[j], 10)
        pg.draw.circle(screen, (255,255,255), ball_projected_pos[j], ball_projected_radius[j], 5)

    draw_axis(screen, axis_bbox, PADDING, x_axis, y_axis, z_axis)
    draw_image(screen, image_bbox, PADDING, pixels, (pen_tip[0], pen_tip[2]))
    
    pg.display.flip()
    clock.tick(FPS)
    pg.display.set_caption(f'FPS: {clock.get_fps()}')
    
pg.quit()
