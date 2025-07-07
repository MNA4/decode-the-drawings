from typing import Generator
import av
import numpy as np

def video_generator(filename: str) -> Generator[tuple[np.ndarray, np.ndarray], None, None]:
    """Generator that yields video frames and audio samples from a video file.
    Args:
        filename (str): Path to the video file.
    Yields:
        tuple: A tuple containing a video frame (as a numpy array)
               and an audio sample (as a numpy array).
    """
    with av.open(filename) as container:
        vid = None
        aud = None
        prev_aud = np.empty((1,))
        for frame in container.decode(video=0, audio=0):
            if isinstance(frame, av.audio.frame.AudioFrame):
                if aud is None:
                    aud = frame.to_ndarray()[0]
                else:
                    aud = np.concatenate((aud, frame.to_ndarray()[0]))
                continue

            elif isinstance(frame, av.video.frame.VideoFrame):
                vid = np.swapaxes(frame.to_rgb().to_ndarray(format="rgb24"), 0, 1)
                if aud is None:
                    yield vid, prev_aud
                else:
                    yield vid, aud
                    prev_aud = aud.copy()
                aud = None

def audio_intensity(audio_sample: np.ndarray) -> float:
    """Calculate the audio intensity from an audio sample.
    Args:
        audio_sample (numpy.ndarray): The audio sample as a 1D numpy array.
    Returns:
        float: The average intensity of the audio sample.
    """
    return np.sqrt(np.mean(audio_sample**2)) if audio_sample.size > 0 else 0.0