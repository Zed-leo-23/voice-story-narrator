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
import re

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


_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")


def split_sentences(text: str) -> list[str]:
    return [t.strip() for t in _SENTENCE_END.split(text.strip()) if t.strip()]


def _spoken_len(sentence: str) -> int:
    return max(1, len(re.sub(r"[^\w]", "", sentence)))


def pauses(wav: np.ndarray, sr: int = SR, min_seconds: float = 0.15) -> list[tuple[int, int]]:
    """(start, end) sample ranges of quiet stretches at least min_seconds long."""
    n = len(wav) // FRAME
    if n == 0:
        return []
    rms = np.sqrt(np.mean(wav[: n * FRAME].reshape(n, FRAME) ** 2, axis=1))
    quiet = rms < max(rms.max() * 0.06, 1e-4)
    runs, start = [], None
    for i in range(n + 1):
        q = i < n and quiet[i]
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) * FRAME >= min_seconds * sr:
                runs.append((start * FRAME, i * FRAME))
            start = None
    return runs


def sentence_passage(wav: np.ndarray, sentences: list[str], sr: int = SR,
                     lo: float = 6.0, hi: float = 15.0, target: float = 11.0) -> tuple[int, int, str, list[int]] | None:
    """A stretch of whole sentences, cut in pauses, whose words are known.

    Each sentence boundary is estimated from the sentences' lengths and snapped
    to the nearest real pause; only boundaries that land in a pause can be a
    passage edge. Returns (start, end, transcript, inner sentence edges) or None.
    """
    runs = pauses(wav, sr)
    if len(sentences) < 2 or not runs:
        return None
    # speech region: after a leading pause, before a trailing one
    t0 = runs[0][1] if runs[0][0] == 0 else 0
    t1 = runs[-1][0] if runs[-1][1] >= len(wav) - FRAME else len(wav)
    lens = [_spoken_len(x) for x in sentences]
    total = sum(lens)
    cum = np.cumsum([0] + lens)
    tol = max(0.8 * sr, 0.08 * (t1 - t0))
    inner = [r for r in runs if t0 < (r[0] + r[1]) // 2 < t1]
    edges: list[int | None] = [t0]
    for k in range(1, len(sentences)):
        est = t0 + (t1 - t0) * cum[k] / total
        near = min(inner, key=lambda r: abs((r[0] + r[1]) // 2 - est), default=None)
        mid = None if near is None else (near[0] + near[1]) // 2
        edges.append(mid if mid is not None and abs(mid - est) <= tol and mid > (edges[-1] or 0) else None)
    edges.append(t1)
    best = None
    for i in range(len(sentences)):
        if edges[i] is None:
            continue
        for j in range(i + 1, len(sentences) + 1):
            if edges[j] is None:
                continue
            dur = (edges[j] - edges[i]) / sr
            expect = (t1 - t0) / sr * (cum[j] - cum[i]) / total
            if not (lo <= dur <= hi) or not (0.75 <= dur / expect <= 1.33):
                continue
            if best is None or abs(dur - target) < abs(best[0] - target):
                inner_edges = [e for e in edges[i + 1:j] if e is not None]
                best = (dur, edges[i], edges[j], " ".join(sentences[i:j]), inner_edges)
    return None if best is None else best[1:]


def clean_passage(wav: np.ndarray, start: int, end: int, inner: list[int], sr: int = SR,
                  pad: float = 0.2, middle: float = 0.1) -> tuple[np.ndarray, int]:
    """Drop breaths from a voice sample: the clone copies every habit of its
    sample, so an inhale between sentences comes back as a "허아?" between its
    own sentences. Only the middle of each quiet stretch at a sentence boundary
    becomes true silence; `pad` seconds next to the speech are kept, because a
    soft sentence ending ("...니다") must stay -- a sample cut short of the words
    its transcript says makes the clone tack those words onto every line.
    Returns (clean audio, number of gaps cleaned)."""
    seg = wav[start:end]
    n = len(seg) // FRAME
    if n < 3:
        return seg, 0
    rms = np.sqrt(np.mean(seg[: n * FRAME].reshape(n, FRAME) ** 2, axis=1))
    # Loud word cores; the soft tail of a word (and its onset) lives within
    # `pad` of a core and is kept, a breath further out in the pause is not.
    speech = rms >= rms.max() * 0.15
    idx = np.flatnonzero(speech)
    if idx.size == 0:
        return seg, 0
    keep = int(pad * sr)
    first = max(0, idx[0] * FRAME - keep)
    last = min(len(seg), (idx[-1] + 1) * FRAME + keep)
    silence = np.zeros(int(middle * sr), dtype=seg.dtype)
    fade = int(0.01 * sr)
    pieces, cursor, cleaned = [], first, 0
    for e in sorted(inner):
        k = (e - start) // FRAME
        if not (0 <= k < n) or speech[k]:
            continue
        a, b = k, k
        while a > 0 and not speech[a - 1]:
            a -= 1
        while b < n - 1 and not speech[b + 1]:
            b += 1
        cut_a, cut_b = a * FRAME + keep, (b + 1) * FRAME - keep
        if cut_b - cut_a < int(0.05 * sr) or cut_a <= cursor or cut_b >= last:
            continue  # pause too short to hold a breath beyond the kept edges
        head = seg[cursor:cut_a].copy()
        if len(head) > fade:
            head[-fade:] *= np.linspace(1, 0, fade, dtype=seg.dtype)
        pieces += [head, silence]
        cursor = cut_b
        cleaned += 1
    tail = seg[cursor:last].copy()
    if cleaned and len(tail) > fade:
        tail[:fade] *= np.linspace(0, 1, fade, dtype=seg.dtype)
    pieces.append(tail)
    return np.concatenate(pieces), cleaned


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audio", required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--transcript", default=None, help="Whole transcript: cut a passage of whole sentences instead")
    args = p.parse_args()

    from omnivoice.utils.audio import load_audio  # engine loader: handles m4a

    wav = load_audio(args.audio, SR).squeeze(0).numpy().astype(np.float32)
    os.makedirs(args.outdir, exist_ok=True)

    if args.transcript is not None:
        found = sentence_passage(wav, split_sentences(args.transcript))
        if found is None:
            print("no clean sentence passage found")
            print(json.dumps({"passage": None}))
            return
        start, end, text, inner = found
        clean, gaps = clean_passage(wav, start, end, inner)
        path = os.path.join(args.outdir, "ref_passage.wav")
        sf.write(path, clean, SR)
        print(f"passage {start / SR:.1f}-{end / SR:.1f}s ({(end - start) / SR:.1f}s -> {len(clean) / SR:.1f}s, "
              f"{gaps} breath gap(s) cleaned): {text}")
        print(json.dumps({"passage": path, "text": text, "seconds": round(len(clean) / SR, 1)}, ensure_ascii=False))
        return

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
