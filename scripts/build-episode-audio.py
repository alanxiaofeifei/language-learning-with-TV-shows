"""Build the Northern Vietnamese phrase clips. Use --force after changing existing cards."""

import argparse
import asyncio
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import NamedTemporaryFile

from aiohttp import ClientError
import edge_tts


ROOT = Path(__file__).resolve().parents[1]
VOICE = "vi-VN-HoaiMyNeural"
RATE = "-20%"
FFPROBE = shutil.which("ffprobe")


def episode_clips():
    result = subprocess.run(
        ["node", "--input-type=module", "-e",
         'import {episodes} from "./site/episodes.js"; console.log(JSON.stringify(episodes))'],
        cwd=ROOT, check=True, capture_output=True, encoding="utf-8"
    )
    clips = []
    for episode in json.loads(result.stdout):
        slug = episode["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", slug):
            raise ValueError(f"Invalid episode ID: {slug}")
        for index, card in enumerate(episode["cards"], 1):
            text = card["vi"].strip()
            if not text:
                raise ValueError(f"Missing phrase in {slug} card {index}")
            clips.append((ROOT / "site" / "audio" / slug / f"{index}.mp3", text))
    if len({path for path, _ in clips}) != len(clips):
        raise ValueError("Duplicate audio paths in episode catalog")
    return clips


def valid(path):
    if not path.is_file() or not path.stat().st_size:
        return False
    if not FFPROBE:
        return True
    probe = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=codec_name,duration", "-of", "json", str(path)],
        capture_output=True, encoding="utf-8"
    )
    if probe.returncode:
        return False
    for stream in json.loads(probe.stdout).get("streams", []):
        duration = stream.get("duration", "")
        if stream.get("codec_name") == "mp3" and duration not in ("", "N/A") and float(duration) > 0:
            return True
    return False


async def build(force):
    clips = episode_clips()
    pending = [(path, text) for path, text in clips if force or not valid(path)]
    parallel = asyncio.Semaphore(3)

    async def synthesize(path, text):
        async with parallel:
            path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=path.parent, suffix=".part", delete=False) as handle:
                temporary = Path(handle.name)
            try:
                speech = edge_tts.Communicate(text, VOICE, rate=RATE, connect_timeout=12, receive_timeout=30)
                await speech.save(str(temporary))
                if not valid(temporary):
                    raise ValueError("TTS returned an invalid clip")
                temporary.replace(path)
                print(f"Built {path.relative_to(ROOT)}", flush=True)
            except (ClientError, OSError, ValueError, edge_tts.exceptions.EdgeTTSException) as error:
                print(f"{path.relative_to(ROOT)}: {type(error).__name__}: {error}", flush=True)
                return path, text
            finally:
                temporary.unlink(missing_ok=True)
        return None

    for attempt in range(6):
        if not pending:
            break
        if attempt:
            await asyncio.sleep(min(2 ** attempt, 10))
        print(f"Pass {attempt + 1}: {len(pending)} clip(s)", flush=True)
        results = await asyncio.gather(*(synthesize(path, text) for path, text in pending))
        pending = [clip for clip in results if clip is not None]
    if pending:
        paths = ", ".join(str(path.relative_to(ROOT)) for path, _ in pending)
        raise SystemExit(f"Audio synthesis incomplete. Rerun to resume: {paths}")
    print(f"Verified {len(clips)} audio clips", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Rebuild clips whose files already exist.")
    asyncio.run(build(parser.parse_args().force))
