# STATUS

Updated 2026-11-28 03:41 (Asia/Saigon, UTC+7).

## Done
- Phase 1 plan: `docs/PLAN-ve-nha-di-con.md`; VLC guide `docs/VLC-bilingual-subtitles.md` (also served as `/vlc.html`).
- Pipeline for all 82 VFC parts: bilingual VI+ZH lines/SRT, daily phrases (food/shopping/work/survival first), rule-based tones + readings, verified original-audio clips. Clip pass-2 finished (82/82 `clips2.done`). Local `site/private` rebuilt 2026-11-28 03:38 UTC+7. `npm test`: 10/10 passed.
- New site: today/day view, 12-week plan (week 1 = tones, consonants, vowels, finals, address terms), part pages with phrase cards + full bilingual transcript + SRT download, SRS review, scenes, whole-show search, VLC page. Piper TTS replaced by original clips; device `speechSynthesis` only as labelled fallback.
- 5S Online + IT scenario archived at `/archive/5s-online/`.
- Cloudflare Access apps for `/private` on tv.alanzhu.dev and tv-preview.alanzhu.dev (reusable policy "Quota dashboard owner via Google"; Worker JWT re-check). No Access apps were widened or deleted. Private files are Worker static assets (not R2), git-ignored, not in Git (~21 MB: 9.5 MB audio, 3.9 MB SRT, 7.8 MB data).
- Site rebuild is on branch `plan/ve-nha-di-con` (commits `3ebe99f`, `93c394c`, docs `76958fa`). Draft PR #1 is open and unmerged. Production `tv.alanzhu.dev` was last deployed 2026-11-27 18:41 UTC+7 (pre-rebuild) and has not been updated.

## Numbers
- Parts: 82 (P06 via Whisper; the other 81 from YouTube auto captions).
- Subtitle / transcript lines: 28,900.
- Phrases: 1,239.
- Verified original-audio clips: **419** (up from 292 after pass-2). Parts with no verified clip: P04, P07, P46.
- LLM: 1,368 DeepSeek `deepseek-chat` calls, 0 GLM fallback. Tokens in `gen/usage.jsonl`: cache-hit 343,168, cache-miss 2,936,834, output 1,351,639. Estimated spend at official 2026 DeepSeek V4.1 Flash rates (legacy `deepseek-chat` alias): about **US$1.25 off-peak** / US$2.50 peak. The usage log has no per-call timestamps; generation clustered around 17:00 UTC Friday 2026-11-27, which is off-peak.

## Preview
- URL: https://tv-preview.alanzhu.dev/
- Live preview is still the 2026-11-28 02:04 UTC+7 deploy (292 clips). The 419-clip `site/private` tree is built locally and ready to upload, but the preview redeploy did **not** go out: `finalize_preview.sh` ran wrangler in a detached environment without `CLOUDFLARE_API_TOKEN`, and this executor shell also has no token after the interruption. Do not deploy production. To finish: in a shell that has the token, `cd /workspace/language-learning-with-TV-shows && CLOUDFLARE_ACCOUNT_ID=ea884be522b147922e986feade4a2cfb npx wrangler deploy --env preview`.
- Anonymous checks (browser User-Agent, 2026-11-28 03:40 UTC+7): `/` → 200 (new site); `/private/data/index.json`, `/private/srt/VeNhaDiCon_P01_08B-aPzkLAg.srt`, and `/private/audio/P01/p01-12.mp3` → 302 to `alaninsights.cloudflareaccess.com` (preview Access AUD). Owner login was not available from this box; sample SRT and clips exist locally under `site/private/` (e.g. `private/srt/VeNhaDiCon_P01_08B-aPzkLAg.srt`, `private/audio/P01/p01-12.mp3`).

## Stages
| Stage | State |
| --- | --- |
| Local commit (site rebuild + docs) | done (`3ebe99f`, `93c394c`, `76958fa`) |
| Pushed to `plan/ve-nha-di-con` | done |
| Merged | no (draft PR #1) |
| Preview deployed | partial — 02:04 UTC+7 build (292 clips) is live; 419-clip rebuild not uploaded (missing API token) |
| Production deployed | no |
| Access / public page verified | preview anonymous 200 + `/private` 302 verified; auth'd asset fetch not done (no owner session) |

## Next
- Redeploy preview with the 419-clip `site/private` tree once `CLOUDFLARE_API_TOKEN` is available in the environment; re-verify Access; then Alan acceptance.
- Production deploy (`npx wrangler deploy`) only when asked.
- Work/factory topic pack (tăng ca, nghỉ phép, hàng lỗi, ca đêm…): search corpus for originals; fallback labelled TTS.
- Optional quality pass: merge YouTube ASR + Whisper hypotheses; proofread week-1/2 parts, especially P04, P07, P46 (no verified clips).
- Progress is per-browser (localStorage); add export/import if Alan uses two devices.
