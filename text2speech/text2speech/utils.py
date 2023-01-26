import numpy as np
from scipy.io.wavfile import write

def write_array_to_wav(array, rate: float | int, fn="output.wav"):
    # writes numpy array to wav file

    scaled = np.int16(array/np.max(np.abs(array)) * 32767)
    write(fn, int(rate), scaled)