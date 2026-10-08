#!/usr/bin/env python3
"""Compose the background-music beds for the Reels.

Every sound is synthesised here (oscillators + filtered noise). No samples,
loops or third-party recordings, so LumiGoods owns the result outright, the
same approach as add_music.py for the ads. Output: music/dayNN.wav

    python music.py

Needs numpy and scipy.
"""
import json
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
HERE = Path(__file__).resolve().parent
NOTES = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(n):
    return 440.0 * 2 ** ((NOTES[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)


def lp(x, f):
    return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)


def hp(x, f):
    return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)


def env(n, a, r):
    e = np.ones(n)
    a, r = min(int(a * SR), n // 2), min(int(r * SR), n // 2)
    e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def saw(f, n, cents=0):
    t = np.arange(n) / SR
    f = f * 2 ** (cents / 1200)
    return 2 * ((f * t) % 1.0) - 1


# One track per Reel: tempo, chord loop (4 bars) and a pluck pattern.
TRACKS = {
    2: dict(bpm=96, chords=[["A2", "E3", "A3", "C4", "E4"], ["F2", "C3", "F3", "A3", "C4"], ["C3", "G3", "C4", "E4", "G4"], ["G2", "D3", "G3", "B3", "D4"]]),
    5: dict(bpm=104, chords=[["C3", "G3", "C4", "E4", "G4"], ["A2", "E3", "A3", "C4", "E4"], ["F2", "C3", "F3", "A3", "C4"], ["G2", "D3", "G3", "B3", "D4"]]),
    9: dict(bpm=92, chords=[["D3", "A3", "D4", "F4", "A4"], ["A#2", "F3", "A#3", "D4", "F4"], ["F2", "C3", "F3", "A3", "C4"], ["C3", "G3", "C4", "E4", "G4"]]),
    12: dict(bpm=100, chords=[["E2", "B2", "E3", "G3", "B3"], ["C3", "G3", "C4", "E4", "G4"], ["G2", "D3", "G3", "B3", "D4"], ["D3", "A3", "D4", "F#4", "A4"]]),
}


def compose(seconds, bpm, chords, seed):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    beat = 60 / bpm
    bar = 4 * beat
    out = np.zeros((2, n))

    t0, i = 0.0, 0
    while t0 < seconds:
        ch = chords[i % len(chords)]
        a, b = int(t0 * SR), min(n, int((t0 + bar) * SR))
        m = b - a
        # Pad: detuned saws, low-passed, slow attack.
        pad = sum(saw(hz(x), m, c) for x in ch[1:] for c in (-7, 7)) / 8
        pad = lp(pad, 1400) * env(m, 0.6, 0.6) * 0.22
        out[0, a:b] += pad
        out[1, a:b] += np.roll(pad, 300)
        # Bass: root, sine + a little saw.
        tt = np.arange(m) / SR
        bass = (np.sin(2 * np.pi * hz(ch[0]) * tt) * 0.8 + lp(saw(hz(ch[0]), m), 300) * 0.2) * env(m, 0.02, 0.3) * 0.32
        out[:, a:b] += bass
        # Pluck arpeggio on 8th notes.
        for k in range(8):
            s = int((t0 + k * beat / 2) * SR)
            if s >= n:
                break
            note = ch[[2, 3, 4, 3, 2, 4, 3, 1][k]]
            ln = min(int(0.45 * SR), n - s)
            tt = np.arange(ln) / SR
            pl = np.sin(2 * np.pi * hz(note) * 2 * tt) * np.exp(-tt * 9) * 0.13
            pan = 0.5 + 0.35 * np.sin(k)
            out[0, s:s + ln] += pl * (1 - pan) * 2
            out[1, s:s + ln] += pl * pan * 2
        t0 += bar
        i += 1

    # Light drums after the first bar: soft kick every other beat, shaker on 8ths.
    t = bar
    k = 0
    while t < seconds - 0.5:
        s = int(t * SR)
        ln = min(int(0.35 * SR), n - s)
        tt = np.arange(ln) / SR
        if k % 4 == 0:
            kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 10) * 0.55
            out[:, s:s + ln] += kick
        sh_len = min(int(0.06 * SR), n - s)
        sh = hp(rng.standard_normal(sh_len), 6000) * np.exp(-np.arange(sh_len) / SR * 60) * (0.05 if k % 2 else 0.03)
        out[:, s:s + sh_len] += sh
        t += beat / 2
        k += 1

    out *= env(n, 0.4, 1.8)
    out /= np.max(np.abs(out)) / 0.6  # about -4.4 dBFS peak: a bed, not a feature
    return out


def write(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    lengths = {2: 25, 5: 30, 9: 30, 12: 30}
    (HERE / "music").mkdir(exist_ok=True)
    for day, spec in TRACKS.items():
        x = compose(lengths[day] + 0.5, spec["bpm"], spec["chords"], seed=day)
        p = HERE / "music" / f"day{day:02d}.wav"
        write(p, x)
        print(p.name)


if __name__ == "__main__":
    main()
