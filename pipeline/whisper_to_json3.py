"""Transcribe audio with faster-whisper (Vietnamese) and write a YouTube-json3-shaped file with word timings,
so captions_to_bilingual.py can consume it. Usage: python pipeline/whisper_to_json3.py AUDIO OUT.json3"""
import json, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
audio, out = sys.argv[1], sys.argv[2]
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", audio, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
pcm = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8", cpu_threads=8)
segs, _ = model.transcribe(pcm, language="vi", beam_size=5, vad_filter=True, word_timestamps=True, condition_on_previous_text=False)
events = []
for s in segs:
    if not s.words: continue
    t0 = int(s.words[0].start * 1000)
    events.append({"tStartMs": t0, "dDurationMs": int(s.end * 1000) - t0,
                   "segs": [{"utf8": w.word.strip(), "tOffsetMs": int(w.start * 1000) - t0} for w in s.words if w.word.strip()]})
json.dump({"events": events, "source": "faster-whisper large-v3-turbo"}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print(len(events), "segments", file=sys.stderr)
