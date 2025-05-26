import numpy as np
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import av
import pygame as pg
from pygame.locals import *

def audio_generator(filename):
    container = av.open(filename)    
    for frame in container.decode(audio=0):
        if isinstance(frame, av.audio.frame.AudioFrame):
            yield frame.to_ndarray()[0]
            
a=audio_generator('6.mp4')
rms=[]
n=0
for i in a:
    val = np.sqrt(np.mean(i**2))
    rms.append(val)
    n+=1
plt.plot(rms)
plt.plot([0, 20000], [0.002, 0.002])
plt.show()
