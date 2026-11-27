# AGENTS.md

Learning site for Northern (Hà Nội) Vietnamese built on the VTV drama *Về nhà đi con* (回家吧，孩子). Owner: Alan (zero-base learner, Chinese native). Live: https://tv.alanzhu.dev (production), https://tv-preview.alanzhu.dev (preview).

## Hard rules
- **Nothing copyrighted in Git.** Transcripts, bilingual SRTs, phrase cards with show lines and audio clips live only in `site/private/` (git-ignored) and are deployed behind Cloudflare Access. Public Git may hold code, the episode list (`data/ve-nha-di-con/parts.json`: public YouTube IDs/titles) and our own teaching content.
- `/private/*` is protected twice: Cloudflare Access apps "TV study private" (tv.alanzhu.dev/private) and "TV study private (preview)" (tv-preview.alanzhu.dev/private), policy = owner's Google login only; and `src/worker.js` re-verifies the Access JWT (`ACCESS_AUD` per env in `wrangler.jsonc`). Never set `workers_dev` or `preview_urls` to true, never widen the Access policy.
- No secrets in code, logs, commits or chat. LLM keys come from env (`DEEPSEEK_API_KEY`, `GLM_API_KEY`). No OpenAI.
- Video source is the **VFC Official** playlist `PLdilN7V0FSOGDiPmg4MVIjP9dfLm0qxWA`, reversed into story order P01–P82. SRT timings only match these uploads.
- Deploy production only when asked: `npx wrangler deploy`. Preview: `npx wrangler deploy --env preview`. Both upload `site/private/` from the local machine, so build it first.

## Layout
- `site/` static app (vanilla ES modules, hash routes). `site/lib/srs.js` (SM-2 style SRS), `site/lib/curriculum.js` (84-day plan), `site/lib/pron.js` (week-1 lessons). `site/archive/5s-online/` = previous 5S Online + IT scenario app (frozen).
- `src/worker.js` Worker: serves assets, guards `/private/*`.
- `pipeline/` data pipeline (Python 3, ffmpeg; faster-whisper + yt-dlp in a venv):
  1. `yt-dlp --write-auto-subs --sub-langs vi-orig --sub-format json3` per part (P06 has no captions → `whisper_to_json3.py`).
  2. `captions_to_bilingual.py CAPS.json3 gen/Pxx` → `Pxx.lines.json` + `Pxx.vi-zh.srt` (LLM regroup + fix + translate; `llm.py` = DeepSeek primary, GLM glm-4.6 fallback; `--reuse` re-times without LLM).
  3. `extract_phrases.py` → `Pxx.phrases.json` (LLM picks; `tones.py` and `reading.py` add tone marks and pinyin-style readings by rule).
  4. `cut_clips.py` → original-audio clips (line span, pad 0.3/0.5 s, ≤ 6 s), kept only if Whisper hears ≥ 60 % of the phrase syllables.
  5. `build_site_data.py WORKDIR` → `site/private/{data,srt,audio}`.
- Work folder on the Grok box: `/workspace/tvshows-work/venhadicon/` (captions, audio, gen/). Do not name work folders dist/build/out.

## Checks
`npm test` (SRS, curriculum, Worker JWT guard, legacy subtitle parser). After deploy: anonymous GET `/private/data/index.json` must redirect to `alaninsights.cloudflareaccess.com`; `/` must be 200.
