# STATUS

Updated 2026-11-28 03:24 (Asia/Saigon, UTC+7). Pass-2 clips and the preview redeploy were still running when this file was written; final clip counts will be filled in after `finalize_preview.sh` finishes.

## Done
- Phase 1 plan: `docs/PLAN-ve-nha-di-con.md`; VLC guide `docs/VLC-bilingual-subtitles.md` (also served as `/vlc.html`).
- Pipeline for all 82 VFC parts: bilingual VI+ZH lines/SRT, daily phrases (food/shopping/work/survival first), rule-based tones + readings, verified original-audio clips (pass 1 complete; pass 2 in progress at time of writing).
- New site: today/day view, 12-week plan (week 1 = tones, consonants, vowels, finals, address terms), part pages with phrase cards + full bilingual transcript + SRT download, SRS review, scenes, whole-show search, VLC page. Piper TTS replaced by original clips; device `speechSynthesis` only as labelled fallback.
- 5S Online + IT scenario archived at `/archive/5s-online/`.
- Cloudflare Access apps for `/private` on tv.alanzhu.dev and tv-preview.alanzhu.dev (reusable policy "Quota dashboard owner via Google"; Worker JWT re-check). Anonymous `/private/*` on the preview host already 302s to Access login. No Access apps were widened or deleted. Private files are Worker static assets (not R2), git-ignored, not in Git.
- Site rebuild is on branch `plan/ve-nha-di-con` (commits `3ebe99f`, `93c394c`). Draft PR #1 is open and unmerged. Production `tv.alanzhu.dev` was last deployed 2026-11-27 18:41 UTC+7 (pre-rebuild) and has not been updated.

## Numbers (pipeline, before final pass-2 rebuild)
- Parts: 82 (P06 via Whisper; the other 81 from YouTube auto captions).
- Subtitle / transcript lines: 28,900.
- Phrases: 1,239.
- Verified clips in the last local `site/private` build (2026-11-28 02:04 UTC+7, pass 1 + whatever pass-2 had finished then): 292. Pass-2 will raise this; see below after redeploy.
- LLM: 1,368 DeepSeek `deepseek-chat` calls, 0 GLM fallback. Tokens in `gen/usage.jsonl`: cache-hit 343,168, cache-miss 2,936,834, output 1,351,639. Estimated spend at official 2026 DeepSeek V4.1 Flash rates (legacy `deepseek-chat` alias): about **US$1.25 off-peak** / US$2.50 peak. The usage log has no per-call timestamps; generation clustered around 17:00 UTC Friday 2026-11-27, which is off-peak.

## Preview
- URL: https://tv-preview.alanzhu.dev/
- A preview Worker was already deployed 2026-11-28 02:04 UTC+7 with the 292-clip build. `finalize_preview.sh` will rebuild `site/private` after pass-2 and deploy **preview only**.
- Anonymous checks already seen: `/` → 200 (new site title 看剧学越南语 · 回家吧，孩子); `/private/data/index.json` → 302 to `alaninsights.cloudflareaccess.com`. Owner login was not available from this box; sample SRT and clips exist locally under `site/private/`.

## Stages
| Stage | State |
| --- | --- |
| Local commit (site rebuild) | done (`3ebe99f`, `93c394c`) |
| Pushed to `plan/ve-nha-di-con` | done |
| Merged | no (draft PR #1) |
| Preview deployed | partial (02:04 UTC+7 build); final pass-2 redeploy pending |
| Production deployed | no |
| Access / public page verified | preview anonymous 200 + /private 302 verified; auth'd asset fetch not done (no owner session) |

## Next
- Finish clip pass-2, rebuild private data, redeploy preview, re-verify Access, fill final clip counts here.
- Alan acceptance on preview, then production deploy (`npx wrangler deploy`) only when asked.
- Work/factory topic pack (tăng ca, nghỉ phép, hàng lỗi, ca đêm…): search corpus for originals; fallback labelled TTS.
- Optional quality pass: merge YouTube ASR + Whisper hypotheses; proofread week-1/2 parts. Some parts still have few or no verified clips after pass 1.
- Progress is per-browser (localStorage); add export/import if Alan uses two devices.
