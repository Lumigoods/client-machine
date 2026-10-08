#!/usr/bin/env python3
"""Add an original background-music bed to the CM ad videos.

The music is composed here, note by note, with simple synthesis (no samples,
loops or third-party recordings), so LumiGoods owns it outright and it is
safe for paid Facebook and Instagram ads. See assets/music/LICENSE.md.

Each ad gets one track, written to its scene timing. The 9:16 and 4:5
versions of an ad share the same track and timing. Originals are never
touched: output goes next to them with "_music" added to the name, and the
video stream is copied without re-encoding.

If a video already has an audio track (e.g. a voiceover), the music is
ducked under it with a sidechain compressor so speech stays clear. The
current videos have no audio, so the music plays on its own.

  python add_music.py Ad1          # render one ad (both versions)
  python add_music.py all          # render all three ads

Needs ffmpeg, numpy and scipy.
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
ROOT = Path(__file__).resolve().parent
VIDEOS = ROOT / "assets" / "creative_backup"
MUSIC = ROOT / "assets" / "music"

NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(name):
    """'A3' -> frequency in Hz."""
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[pitch] + 12 * (octave + 1) - 69) / 12)


def lowpass(x, cutoff, order=2):
    return sosfilt(butter(order, min(cutoff, SR / 2 - 100), "low", fs=SR, output="sos"), x)


def highpass(x, cutoff, order=2):
    return sosfilt(butter(order, cutoff, "high", fs=SR, output="sos"), x)


def saw(freq, n, detune_cents=0.0, phase=0.0):
    f = freq * 2 ** (detune_cents / 1200)
    t = np.arange(n) / SR
    return 2 * ((f * t + phase) % 1.0) - 1


def adsr(n, a, d, s, r):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    env = np.full(n, s, dtype=float)
    env[:a] = np.linspace(0, 1, a, endpoint=False)[: n]
    if a < n:
        env[a:a + d] = np.linspace(1, s, d, endpoint=False)[: max(0, n - a)]
    if r and n > r:
        env[-r:] *= np.linspace(1, 0, r)
    return env


class Track:
    """A stereo buffer with a few instruments that write into it."""

    def __init__(self, seconds, bpm):
        self.n = int(seconds * SR)
        self.bpm = bpm
        self.beat = 60.0 / bpm
        self.buses = {k: np.zeros((2, self.n)) for k in ("pad", "pluck", "bass", "drums", "fx")}
        self.kicks = []

    def _add(self, bus, start, sig, pan=0.0):
        i = int(start * SR)
        if i >= self.n:
            return
        sig = sig.copy()
        tail = min(len(sig), int(0.01 * SR))  # 10 ms fade so no sound ends with a click
        sig[-tail:] *= np.linspace(1, 0, tail)
        sig = sig[: self.n - i]
        left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.buses[bus][0, i:i + len(sig)] += sig * left
        self.buses[bus][1, i:i + len(sig)] += sig * right

    # instruments -------------------------------------------------------------
    def pad(self, start, dur, notes, vol=0.12, cutoff=1800, gain=2.2):
        n = int((dur + 1.2) * SR)
        for k, note in enumerate(notes):
            f = hz(note)
            for cents, pan in ((-7, -0.6), (0, 0.0), (7, 0.6)):
                v = saw(f, n, cents, phase=(k * 0.37 + cents * 0.01) % 1)
                v = lowpass(v, cutoff) * adsr(n, 0.12, 0.3, 0.85, 1.2)
                self._add("pad", start, v * vol * gain / len(notes), pan)

    def pluck(self, start, note, vol=0.16, decay=0.22, cutoff=3500, pan=0.0):
        n = int(0.9 * SR)
        f = hz(note)
        v = 0.6 * saw(f, n) + 0.4 * np.sign(np.sin(2 * np.pi * f * np.arange(n) / SR))
        env = np.exp(-np.arange(n) / (decay * SR))
        v = lowpass(v * env, cutoff) * adsr(n, 0.003, 0, 1, 0.05)
        self._add("pluck", start, v * vol * 2.2, pan)

    def bass(self, start, dur, note, vol=0.13):
        n = int(dur * SR)
        t = np.arange(n) / SR
        f = hz(note)
        v = np.tanh(1.6 * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)))
        self._add("bass", start, lowpass(v, 400) * adsr(n, 0.008, 0.1, 0.85, 0.03) * vol)

    def kick(self, start, vol=0.9):
        n = int(0.45 * SR)
        t = np.arange(n) / SR
        freq = 45 + 85 * np.exp(-t * 28)
        v = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 7.5)
        click = lowpass(np.random.default_rng(1).normal(0, 1, 240), 3000) * np.exp(-np.arange(240) / 40)
        v[:240] += 0.15 * click
        self._add("drums", start, v * vol)
        self.kicks.append(start)

    def clap(self, start, vol=0.28):
        n = int(0.25 * SR)
        noise = np.random.default_rng(int(start * 1000)).normal(0, 1, n)
        env = np.zeros(n)
        for off in (0, 0.011, 0.022):  # three quick hits, like hands
            i = int(off * SR)
            env[i:] += np.exp(-np.arange(n - i) / (0.045 * SR))
        v = sosfilt(butter(2, [900, 4500], "band", fs=SR, output="sos"), noise * env)
        self._add("drums", start, v * vol / 2, pan=0.1)

    def hat(self, start, vol=0.07, length=0.05, pan=0.25):
        n = int(0.12 * SR)
        noise = np.random.default_rng(int(start * 997)).normal(0, 1, n)
        v = highpass(noise, 7000) * np.exp(-np.arange(n) / (length * SR))
        self._add("drums", start, v * vol, pan)

    def riser(self, start, dur, vol=0.10):
        n = int(dur * SR)
        noise = np.random.default_rng(7).normal(0, 1, n)
        out = np.zeros(n)
        chunk = SR // 50
        for i in range(0, n, chunk):  # sweep the band upwards
            frac = i / n
            lo = 300 + 3000 * frac
            seg = noise[max(0, i - 2048):i + chunk]
            filt = sosfilt(butter(2, [lo, lo * 2.5], "band", fs=SR, output="sos"), seg)
            out[i:i + chunk] = filt[-len(out[i:i + chunk]):]
        self._add("fx", start, out * np.linspace(0, 1, n) ** 2 * vol)

    def impact(self, start, vol=0.35):
        n = int(1.6 * SR)
        t = np.arange(n) / SR
        boom = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t * 10)) / SR) * np.exp(-t * 3)
        air = lowpass(np.random.default_rng(3).normal(0, 1, n), 2500) * np.exp(-t * 5) * 0.25
        self._add("fx", start, (boom + air) * vol)

    # helpers -----------------------------------------------------------------
    def t(self, bar, beat=0.0):
        """Seconds at a bar (4/4) and beat."""
        return (bar * 4 + beat) * self.beat

    def arp(self, bar_from, bar_to, chords, pattern, step=0.5, **kw):
        """Arpeggiate one chord per bar; pattern indexes into the chord."""
        b = bar_from
        while b < bar_to:
            chord = chords[int(b - bar_from) % len(chords)]
            k = 0
            beat = 0.0
            while beat < 4 and b + beat / 4 < bar_to:
                note = chord[pattern[k % len(pattern)] % len(chord)]
                pan = 0.35 if k % 2 else -0.35
                self.pluck(self.t(b, beat), note, pan=pan, **kw)
                beat += step
                k += 1
            b += 1

    # mixdown -----------------------------------------------------------------
    def render(self):
        # sidechain-style pump: pad and bass dip under each kick
        pump = np.ones(self.n)
        for k in self.kicks:
            i = int(k * SR)
            m = min(self.n - i, int(0.32 * SR))
            if m > 0:
                shape = 0.55 + 0.45 * np.linspace(0, 1, m) ** 0.6
                ramp = min(m, int(0.006 * SR))
                shape[:ramp] = np.linspace(1, shape[ramp - 1], ramp)
                pump[i:i + m] = np.minimum(pump[i:i + m], shape)
        b = self.buses
        dry = b["pad"] * pump + b["bass"] * pump + b["pluck"] + b["drums"] + b["fx"]
        send = b["pad"] * 0.5 + b["pluck"] * 0.6 + b["drums"] * 0.12 + b["fx"] * 0.4
        ir_n = int(1.8 * SR)
        rng = np.random.default_rng(11)
        decay = np.exp(-np.arange(ir_n) / (0.45 * SR))
        ir = [lowpass(rng.normal(0, 1, ir_n) * decay, 6000) for _ in range(2)]
        wet = np.stack([fftconvolve(send[c], ir[c])[: self.n] for c in range(2)])
        wet /= np.max(np.abs(wet)) + 1e-9
        mix = dry + 0.18 * wet * np.max(np.abs(dry))
        return mix / (np.max(np.abs(mix)) + 1e-9) * 0.89


# --- compositions, one per ad, timed to its scenes ---------------------------

def ad1_problem(seconds):
    """Problem -> solution. 100 BPM, 2.4 s bars; the CLIENT MACHINE reveal at
    12.0 s lands on bar 5.
      0.0-4.8   'You can edit.'            light, confident arpeggio
      4.8-12.0  'But where's the next client?' / the questions: minor, a
                ticking hat like a clock, kick enters, riser into the reveal
      12.0-end  'CLIENT MACHINE' + price: lifts to major, full groove
    """
    tr = Track(seconds, 100)
    am, f, dm, e = (["A3", "C4", "E4", "G4"], ["F3", "A3", "C4", "E4"],
                    ["D3", "F3", "A3", "C4"], ["E3", "G#3", "B3", "D4"])
    c, g, am2, fmaj = (["C4", "E4", "G4", "B4"], ["G3", "B3", "D4", "F#4"],
                       ["A3", "C4", "E4", "G4"], ["F3", "A3", "C4", "E4"])
    # A: you can edit
    tr.pad(tr.t(0), tr.t(2), am, vol=0.08, cutoff=1200)
    tr.arp(0, 2, [am, am], [0, 2, 1, 3], step=0.5, vol=0.11, cutoff=2800)
    tr.bass(tr.t(1), tr.t(1), "A2", vol=0.08)
    # B: the problem
    for i, (ch, root) in enumerate(((f, "F2"), (dm, "D2"), (e, "E2"))):
        bar = 2 + i
        tr.pad(tr.t(bar), tr.t(1), ch, vol=0.10, cutoff=1000 + 300 * i)
        tr.bass(tr.t(bar), tr.t(1), root, vol=0.11)
        tr.arp(bar, bar + 1, [ch], [0, 1, 2, 1], step=1.0, vol=0.09, cutoff=2000)
        for beat in range(4):
            tr.kick(tr.t(bar, beat), vol=0.45 + 0.1 * i)
            tr.hat(tr.t(bar, beat + 0.5), vol=0.05)
    tr.riser(tr.t(4), tr.t(1))
    # C: the system + price
    tr.impact(tr.t(5))
    prog = [(c, "C2"), (g, "G2"), (am2, "A2"), (fmaj, "F2")]
    bar = 5
    while tr.t(bar) < seconds:
        ch, root = prog[(bar - 5) % 4]
        tr.pad(tr.t(bar), tr.t(1), ch, vol=0.11, cutoff=2600)
        tr.bass(tr.t(bar), tr.t(0, 1.5), root)
        tr.bass(tr.t(bar, 2), tr.t(0, 2), root)
        tr.arp(bar, bar + 1, [ch], [0, 2, 3, 1, 2, 3, 1, 2], step=0.5, vol=0.13, cutoff=4200)
        for beat in range(4):
            tr.kick(tr.t(bar, beat))
            tr.hat(tr.t(bar, beat + 0.5), vol=0.08)
            tr.hat(tr.t(bar, beat + 0.75), vol=0.035, pan=-0.25)
        tr.clap(tr.t(bar, 1))
        tr.clap(tr.t(bar, 3))
        bar += 1
    return tr.render()


ADS = {
    "Ad1": {"stem": "CM_Ad1_Problem_FINAL", "compose": ad1_problem, "bpm": 100,
            "mood": "problem -> solution: tense minor build, lifts to major at the reveal"},
}


# --- export -------------------------------------------------------------------

def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    return float(info["format"]["duration"]), has_audio


def write_wav(path, stereo):
    pcm = (np.clip(stereo.T, -1, 1) * 32767).astype("<i2").tobytes()
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)


def render_ad(key):
    ad = ADS[key]
    durations = {r: probe(VIDEOS / f"{ad['stem']}_{r}.mp4") for r in ("9x16", "4x5")}
    seconds = durations["4x5"][0]
    if abs(durations["9x16"][0] - seconds) > 0.05:
        sys.exit(f"{key}: the 9x16 and 4x5 versions differ in length; check them first.")

    MUSIC.mkdir(parents=True, exist_ok=True)
    raw = MUSIC / f"{ad['stem']}_music_raw.wav"
    track = MUSIC / f"{ad['stem']}_music.wav"
    write_wav(raw, ad["compose"](seconds))
    # Loudness for social video (-16 LUFS, -1.5 dBTP) plus a short fade-in
    # and a 1.5 s fade-out ending exactly with the video.
    fade_out = 1.5
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
                    "-af", f"afade=t=in:d=0.3,afade=t=out:st={seconds - fade_out:.3f}:d={fade_out},"
                           "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", str(SR), str(track)], check=True)
    raw.unlink()

    for ratio, (dur, has_audio) in durations.items():
        src = VIDEOS / f"{ad['stem']}_{ratio}.mp4"
        dst = VIDEOS / f"{ad['stem']}_{ratio}_music.mp4"
        if has_audio:
            # Duck the music ~10 dB under existing audio (voiceover/SFX).
            fc = ("[1:a]volume=1.0[m];[0:a]asplit[vo][sc];"
                  "[m][sc]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[duck];"
                  "[vo][duck]amix=inputs=2:normalize=0[a]")
            amap = ["-filter_complex", fc, "-map", "0:v", "-map", "[a]"]
        else:
            amap = ["-map", "0:v", "-map", "1:a"]
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(src), "-i", str(track), *amap,
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(SR),
                        "-t", f"{dur:.3f}", "-movflags", "+faststart", str(dst)], check=True)
        print(f"{dst.relative_to(ROOT)}  ({'ducked under existing audio' if has_audio else 'music only'})")


def main():
    keys = list(ADS) if sys.argv[1:] == ["all"] else sys.argv[1:]
    if not keys or any(k not in ADS for k in keys):
        sys.exit(f"Usage: python add_music.py {'|'.join(ADS)}|all")
    for k in keys:
        render_ad(k)


if __name__ == "__main__":
    main()
