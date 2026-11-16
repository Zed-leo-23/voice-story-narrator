"""Split a two-paragraph voice recording at the pause between the paragraphs.

The engine accepts at most 20 seconds of reference audio together with its
transcript, so a ~30 second recording read as two paragraphs (with a short
pause between them) is cut into two pieces that each match one paragraph.

Run with the engine on PYTHONPATH (it loads m4a/mp3 via the engine's loader):
    python cut_reference.py --audio "Yk voice.m4a" --outdir out
Prints a JSON line {"part1": path, "part2": path, "durations": [...]}.
"""

import argparse
import json
import os

import numpy as np
import soundfile as sf

SR = 24000
FRAME = int(0.02 * SR)  # 20 ms


def find_cut(wav: np.ndarray, sr: int = SR) -> tuple[int, bool]:
    """Sample index at the middle of the longest quiet stretch within the
    middle 30-70% of the clip. Returns (index, found_pause)."""
    n = len(wav) // FRAME
    if n < 10:
        return len(wav) // 2, False
    rms = np.sqrt(np.mean(wav[: n * FRAME].reshape(n, FRAME) ** 2, axis=1))
    quiet = rms < max(rms.max() * 0.06, 1e-4)
    lo, hi = int(n * 0.3), int(n * 0.7)
    best_len, best_start, run_start = 0, None, None
    for i in range(lo, hi + 1):
        q = i < hi and quiet[i]
        if q and run_start is None:
            run_start = i
        elif not q and run_start is not None:
            if i - run_start > best_len:
                best_len, best_start = i - run_start, run_start
            run_start = None
    if best_start is None or best_len * FRAME < 0.25 * sr:  # no real pause (>=0.25s)
        return len(wav) // 2, False
    return (best_start + best_len // 2) * FRAME, True


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audio", required=True)
    p.add_argument("--outdir", required=True)
    args = p.parse_args()

    from omnivoice.utils.audio import load_audio  # engine loader: handles m4a

    wav = load_audio(args.audio, SR).squeeze(0).numpy().astype(np.float32)
    cut, found = find_cut(wav)
    if not found:
        print("WARNING: no clear pause found between the paragraphs -- cutting in the middle")
    os.makedirs(args.outdir, exist_ok=True)
    paths = []
    for i, piece in enumerate((wav[:cut], wav[cut:]), 1):
        path = os.path.join(args.outdir, f"ref_part{i}.wav")
        sf.write(path, piece, SR)
        paths.append(path)
    durations = [round(len(wav[:cut]) / SR, 1), round(len(wav[cut:]) / SR, 1)]
    print(f"recording {len(wav) / SR:.1f}s cut at {cut / SR:.1f}s -> {durations}")
    print(json.dumps({"part1": paths[0], "part2": paths[1], "durations": durations}))


if __name__ == "__main__":
    main()
