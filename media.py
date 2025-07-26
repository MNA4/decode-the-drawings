from typing import Generator, Tuple
import av
import numpy as np

def video_generator(
    filename: str
) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
    """
    Generator that yields (video_frame, audio_chunk) pairs, where:
      - video_frame has shape (W, H, 3) uint8 RGB
      - audio_chunk is a 1D int16 array of samples decoded since the last frame
    """
    container = av.open(filename)
    video_stream = container.streams.video[0]
    audio_stream = container.streams.audio[0]
    video_stream.thread_type = "AUTO"
    audio_stream.thread_type = "AUTO"

    audio_buffer = []
    previous_audio = np.empty((0,), dtype=np.int16)
    for packet in container.demux((audio_stream, video_stream)):
        if packet.stream is audio_stream:
            for af in packet.decode():
                audio_buffer.append(af.to_ndarray()[0])

        elif packet.stream is video_stream:
            for vf in packet.decode():
                # grab only the audio since last frame
                if audio_buffer:
                    aud = np.concatenate(audio_buffer)
                    previous_audio = aud
                    audio_buffer.clear()
                else:
                    aud = previous_audio

                # get H×W×3 and transpose to W×H×3
                frame_hwc = vf.to_ndarray(format="rgb24")
                vid = frame_hwc.transpose(1, 0, 2)

                yield vid, aud

    container.close()

def audio_intensity(audio_sample: np.ndarray) -> float:
    """Calculate the audio intensity from an audio sample.
    Args:
        audio_sample (numpy.ndarray): The audio sample as a 1D numpy array.
    Returns:
        float: The average intensity of the audio sample.
    """
    return np.sqrt(np.mean(audio_sample**2)) if audio_sample.size > 0 else 0.0