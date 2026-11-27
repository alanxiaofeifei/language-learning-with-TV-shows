"""Build Northern Vietnamese phrase audio. Requires piper-tts, huggingface_hub, FFmpeg and Node."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import wave

from piper import PiperVoice, SynthesisConfig


ROOT = Path(__file__).resolve().parents[1]
MODEL_REPO = "CakeByVPBank/piper-pgl-v4-vi_VN-version39_epoch39"
REVISION = "8ea50134bea762f6a1faac671e1a33c41871289c"
MODEL_FILE = "vi_VN-csa-voice-piper-v3-medium.onnx"
MODEL_SHA256 = "99424831c88afec929eba3aef83a1b3d92f261b0bdc771bc2458f7f1ba63b6d2"
CONFIG_SHA256 = "919c6f45f16e6549e5f72ae4961bf191abbb661830574e7786ab13da496a408e"
VOICE = f"{MODEL_REPO}@{REVISION}; speaker=0; length_scale=1.20"


def voice_model(model_path):
    if model_path is None:
        from huggingface_hub import hf_hub_download

        model_path = Path(hf_hub_download(MODEL_REPO, MODEL_FILE, revision=REVISION))
        hf_hub_download(MODEL_REPO, MODEL_FILE + ".json", revision=REVISION)
    config = Path(str(model_path) + ".json")
    for path, expected in ((model_path, MODEL_SHA256), (config, CONFIG_SHA256)):
        with path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
                raise ValueError(f"Unexpected voice model or config: {path}")
    return PiperVoice.load(model_path, config_path=config)


def episode_clips():
    result = subprocess.run(
        ["node", "--input-type=module", "-e",
         'import {episodes} from "./site/archive/5s-online/episodes.js"; console.log(JSON.stringify(episodes))'],
        cwd=ROOT, check=True, capture_output=True, encoding="utf-8",
    )
    clips = {}
    for episode in json.loads(result.stdout):
        slug = episode["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", slug):
            raise ValueError(f"Invalid episode ID: {slug}")
        for index, card in enumerate(episode["cards"], 1):
            text = card["vi"].strip()
            key = Path(slug, f"{index}.mp3")
            if not text or key in clips:
                raise ValueError(f"Missing or duplicate clip: {key}")
            clips[key] = text
    return clips


def is_current(path, text):
    if not path.is_file() or not path.stat().st_size:
        return False
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=codec_name,duration:format_tags=title,comment", "-of", "json", str(path)],
        capture_output=True, encoding="utf-8",
    )
    if probe.returncode:
        return False
    info = json.loads(probe.stdout)
    tags = info.get("format", {}).get("tags", {})
    streams = info.get("streams", [])
    return (tags.get("title") == text and tags.get("comment") == VOICE
            and bool(streams) and streams[0]["codec_name"] == "mp3"
            and float(streams[0].get("duration", 0)) > 0)


def build(model_path, output, force):
    clips = episode_clips()
    jobs = {path: text for path, text in clips.items() if force or not is_current(output / path, text)}
    if jobs:
        voice = voice_model(model_path)
        options = SynthesisConfig(speaker_id=0, length_scale=1.2, noise_scale=0.667, noise_w_scale=0.8)
        output.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix="episode-tts-", dir=output.parent) as work:
            for path, text in jobs.items():
                file = Path(work, path)
                file.parent.mkdir(parents=True, exist_ok=True)
                buf = BytesIO()
                with wave.open(buf, "wb") as wav:
                    voice.synthesize_wav(text, wav, syn_config=options)
                subprocess.run([
                    "ffmpeg", "-loglevel", "error", "-nostdin", "-f", "wav", "-i", "pipe:0",
                    "-c:a", "libmp3lame", "-q:a", "3", "-metadata", f"title={text}",
                    "-metadata", f"comment={VOICE}", str(file),
                ], input=buf.getvalue(), check=True)
                if not is_current(file, text):
                    raise ValueError(f"Invalid generated clip: {path}")
                print(f"Built {path}", flush=True)
            for path in jobs:
                destination = output / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                Path(work, path).replace(destination)
    print(f"Verified {len(clips)} Ngoc Lan clips", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, help="Pinned ONNX file with its adjacent .json config")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "site" / "archive" / "5s-online" / "audio")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    build(args.model, args.out_dir, args.force)
