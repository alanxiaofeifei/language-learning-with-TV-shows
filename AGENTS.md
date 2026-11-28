# AGENTS.md

Multi-language learning site (hash routes, language picker at `#/`). Vietnamese (Northern / Hà Nội) is the first ready language, built on the VTV drama *Về nhà đi con* (回家吧，孩子), with a 12-week short track and a 5-year long track on the same 82 parts. Chinese (《都挺好》 All is Well, official 正午阳光 YouTube uploads, audio clips) and US English (*Friends* S01–S02, text only: no audio/video/clips) are ready via the generic multi-show pipeline. Canadian French, Tokyo Japanese, US/Latin American Spanish and Hong Kong Cantonese are placeholders with planned picks in `site/lib/catalog.js`. Owner: Alan. Live: https://tv.alanzhu.dev (production), https://tv-preview.alanzhu.dev (preview).

## Hard rules
- **Nothing copyrighted in Git.** Transcripts, bilingual SRTs, phrase cards with show lines and audio clips live only in `site/private/` (git-ignored) and are deployed behind Cloudflare Access. Public Git may hold code, the episode list (`data/ve-nha-di-con/parts.json`: public YouTube IDs/titles) and our own teaching content.
- `/private/*` is protected twice: Cloudflare Access apps "TV study private" (`tv.alanzhu.dev/private`) and "TV study private (preview)" (`tv-preview.alanzhu.dev/private`), each using the reusable policy "Quota dashboard owner via Google" (owner Google login only); and `src/worker.js` re-verifies the Access JWT (`ACCESS_AUD` per env in `wrangler.jsonc`). Never set `workers_dev` or `preview_urls` to true, never widen the Access policy, never delete Access apps.
- No secrets in code, logs, commits or chat. LLM keys come from env (`DEEPSEEK_API_KEY`, `GLM_API_KEY`). No OpenAI, no Codex CLI, no Antigravity/agy for this project unless Alan says otherwise.
- Video source is the **VFC Official** playlist `PLdilN7V0FSOGDiPmg4MVIjP9dfLm0qxWA`, reversed into story order P01–P82. SRT timings only match these uploads.
- Deploy production only when asked: `npx wrangler deploy`. Preview: `npx wrangler deploy --env preview`. Both upload `site/private/` from the local machine, so build it first with `python3 pipeline/build_site_data.py WORKDIR`. Private assets use Worker static assets under `/private/*` (no R2 unless a later change is approved; stop if a paid plan would be required).
- Long pipeline jobs on the shared box must be started with `setsid nohup` so they survive agent interruptions. Do not restart or kill a live `cut_clips.py` / `clip_worker2.sh` / `finalize_preview.sh`.

## Layout
- `site/` static app (vanilla ES modules, hash routes). `site/lib/catalog.js` (languages, shows, routes and legacy aliases), `site/lib/curriculum.js` (12-week / 84-day short plan), `site/lib/long-curriculum.js` (260-week / 6-stage long plan), `site/lib/srs.js` (SM-2 style SRS), `site/lib/pron.js` (week-1 lessons), `site/lib/motion.js` (page transitions, reduced-motion), `site/lib/show-curriculum.js` (short/long plans for multi shows), `site/multi.js` (views for multi shows), `site/lib/i18n.js` + `site/lib/prefs.js` (zh/vi UI, per-user defaults), `site/shows/<id>/episodes.json` (public episode lists). `site/archive/5s-online/` = previous 5S Online + IT scenario app (frozen).
- `src/worker.js` Worker: serves assets, guards `/private/*`, serves `/private/me.json`.
- `pipeline/` data pipeline (Python 3, ffmpeg; faster-whisper + yt-dlp in a venv):
  1. `yt-dlp --write-auto-subs --sub-langs vi-orig --sub-format json3` per part (P06 has no captions → `whisper_to_json3.py`).
  2. `captions_to_bilingual.py CAPS.json3 gen/Pxx` → `Pxx.lines.json` + `Pxx.vi-zh.srt` (LLM regroup + fix + translate; `llm.py` = DeepSeek primary, GLM glm-4.6 fallback; `--reuse` re-times without LLM).
  3. `extract_phrases.py` → `Pxx.phrases.json` (LLM picks; `tones.py` and `reading.py` add tone marks and pinyin-style readings by rule).
  4. `cut_clips.py` pass 1: original-audio clips (line span, pad 0.3/0.5 s, ≤ 6 s), kept if Whisper hears ≥ 60 % of the phrase syllables. Pass 2 (`--mode window --min-score 0.75`): only phrases still missing a clip; locate the phrase with word timestamps in a wider window.
  5. `build_site_data.py WORKDIR` → `site/private/{data,srt,audio}`.
- Work folder on the Grok box: `/workspace/tvshows-work/venhadicon/` (captions, audio, gen/). Helpers: `resume.sh`, `clip_worker2.sh`, `finalize_preview.sh`. Do not name work folders dist/build/out.

## Multi-show pipeline (`pipeline/multi/`, 都挺好 + Friends)
Show config lives in `pipeline/multi/common.py` (`SHOWS`). Every step is re-runnable and skips existing output (`--only EP01,EP02` / `S01E01` / `1-5`, `--force` to redo). Python: `/home/box/venvs/ytdlp/bin/python`. WORKDIRs: `/workspace/tvshows-work/multi/dtt` (playlist.tsv, subs/, audio/) and `/workspace/tvshows-work/multi/friends` (srt/, episodes.json); outputs go to `WORKDIR/gen/`.
1. `ingest_youtube_json3.py SHOW WORK` (youtube-official): zh-Hans + vi share cues, en attached by max overlap → `CODE.lines.json` `{i,start,end,zh,py,vi,en}` (ms; pinyin by pypinyin, may miss polyphones).
2. `ingest_srt.py SHOW WORK` (text-only): SRT → `{i,start,end,en}`; tags/music notes stripped.
3. `translate_lines.py SHOW WORK`: fills missing `zh`/`vi` (Friends) in batches via `llm.py`; saves after every batch.
4. `extract_phrases_multi.py SHOW WORK`: ~15 cards/episode, level (HSK1–6/HSK7-9 or CEFR), `explain_zh`/`explain_vi`, `usage_zh`/`usage_vi`, source line + time. Phrases not found in the source line are dropped.
5. `cut_clips_cues.py SHOW WORK` (youtube-official only): mp3 per card from its cue (−0.25 s/+0.4 s, ≤ 7 s, mono 64 kbps); skips episodes whose audio is missing.
6. `build_show_data.py SHOW WORK` → `site/private/shows/<id>/{index.json, eps/CODE.json, srt/*.srt, audio/CODE/*.mp3}` (zh+vi and zh+en SRT for 都挺好; en+zh and en+vi for Friends). Rebuilds only that show's folder.
7. `episodes_public.py SHOW WORK` → `site/shows/<id>/episodes.json` (public: episode numbers, YouTube IDs, durations, titles; tracked in Git).
Set `LLM_USAGE_LOG=/path/usage.jsonl` to record token usage. Friends is text only: never add audio, video or clips for it.

## Per-user defaults
`GET /private/me.json` (Worker, after the JWT check) returns `{visibleLangs, uiLang, explainLang, name}` from the secret `USER_PREFS` (JSON: lowercase email → prefs); unknown users get `{null, "zh", "zh", null}`. It never echoes the email. Set it with `npx wrangler secret put USER_PREFS` (and `--env preview`) only when Alan asks; never put emails in `wrangler.jsonc` or Git. `visibleLangs` is display only, not authorization. The UI (`site/lib/prefs.js`, `site/lib/i18n.js`) falls back to defaults for anonymous users; localStorage overrides via the header menu.

## Checks
`npm test` (catalog/routes, short and long curricula incl. 46/48-episode show plans, SRS, Worker JWT guard + `/private/me.json`, i18n/prefs, legacy subtitle parser, `scripts/check-no-private.sh`). After a preview or production deploy: anonymous GET `/` must be 200; anonymous GET `/private/data/index.json` must redirect (302) to `alaninsights.cloudflareaccess.com`. If you cannot log in as the owner, confirm a sample SRT and clip exist under `site/private/` (the tree that wrangler uploads).
