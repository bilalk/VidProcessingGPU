import numpy as np
import wave

SR = 44100
DUR = 30.0
N = int(SR * DUR)
mix = np.zeros(N)

# Gentle ambient bed: Am - C - F - G pads + soft pluck, no drums (reel background)
CH = [
    ([110.00, 130.81, 164.81], 55.00),
    ([130.81, 164.81, 196.00], 65.41),
    ([87.31, 110.00, 130.81], 43.65),
    ([98.00, 123.47, 146.83], 49.00),
]
STEP = 7.5

for ci, (chord, root) in enumerate(CH):
    s = ci * STEP
    i0 = int(s * SR)
    n = min(int((STEP + 1.5) * SR), N - i0)
    e = np.ones(n)
    na = min(int(2.2 * SR), n); nr = min(int(3.0 * SR), n)
    if na > 0:
        e[:na] = np.linspace(0, 1, na) ** 2
    if nr > 0:
        e[-nr:] *= np.linspace(1, 0.03, nr) ** 2
    tt = np.arange(n) / SR
    seg = np.zeros(n)
    for f in chord:
        w = (np.sin(2 * np.pi * f * tt)
             + 0.45 * np.sin(2 * np.pi * f * 2.0 * tt + 0.2)
             + 0.22 * np.sin(2 * np.pi * f * 2.997 * tt)) / 1.67
        seg += 0.10 * w
    # soft bass
    seg += 0.11 * np.sin(2 * np.pi * root * tt)
    mix[i0:i0 + n] += seg * e

# sparse soft pluck melody (pentatonic feel)
NOTES = [220.0, 261.63, 329.63, 392.0, 440.0, 523.25]
rng = np.random.default_rng(11)
tcur = 1.5
while tcur < 28.5:
    f = NOTES[rng.integers(0, len(NOTES))]
    i0 = int(tcur * SR); n = int(0.9 * SR)
    tt = np.arange(n) / SR
    w = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 4.5) + 0.3 * np.sin(2 * np.pi * f * 2 * tt) * np.exp(-tt * 7)
    mix[i0:i0 + n] += w * 0.045
    tcur += float(rng.choice([1.5, 2.0, 2.5, 3.0]))

mix = np.tanh(mix)
mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.6
fi = int(1.0 * SR); fo = int(2.0 * SR)
mix[:fi] *= np.linspace(0, 1, fi)
mix[-fo:] *= np.linspace(1, 0, fo)
d = int(0.008 * SR)
right = np.concatenate([np.zeros(d), mix[:-d]])
pcm = (np.stack([mix, right], axis=1) * 32767).astype(np.int16)
with wave.open('/root/reels/bed.wav', 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('BED_OK /root/reels/bed.wav', flush=True)
