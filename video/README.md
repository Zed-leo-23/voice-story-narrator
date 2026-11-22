# video/

`make_video.py` turns one story's narration into a draft video: one image
per scene with a slow Ken Burns zoom, burned-in subtitles, muxed with the
narration audio, plus a thumbnail.

```bash
# needs an ffmpeg build with libass (the subtitles filter) --
# Homebrew's plain `ffmpeg` formula doesn't have it:
brew install ffmpeg-full
# (make_video.py finds it automatically at /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg)

gh release download story-samani -R Zed-leo-23/voice-story-narrator -D video/
python3 video/make_video.py \
    --audio video/full_story.wav \
    --timeline video/timeline.json \
    --outdir video/out/samani
```

Needs a real `timeline.json` from the release (narrate.py has written one
since commit `dd02896`, 2026-11-22). Releases made before that commit, or
by a Kaggle run whose repo clone predated it, won't have one yet -- the
next run after that commit should.

## Known gap: scene art

`scene_card()` only draws a placeholder gradient card with the scene
number -- there is no illustration step. Every placeholder frame is
watermarked "PLACEHOLDER ART -- not for upload" so a draft can't be
mistaken for something ready to publish. Swap `scene_card()` for real
per-scene artwork (fixed style, no real people or other channels' art,
per `docs/youtube-pipeline.md` section 2) before anything ships.

## test_fixtures/

`samani_timeline.synthetic.json` is **not** real narrate.py output --
story-samani's release predates the real timeline.json feature, so this
reconstructs scene/line timing by splitting the narration's known total
duration proportionally by text length. It's only good for exercising the
video-assembly code path (frame counts, concat, subtitle burn-in, muxing);
its per-line timestamps will not match the real audio.
