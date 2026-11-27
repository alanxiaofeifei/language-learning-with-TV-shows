# STATUS

Updated 2026-11-28 (UTC+7).

## Done
- Phase 1 plan: `docs/PLAN-ve-nha-di-con.md`; VLC guide `docs/VLC-bilingual-subtitles.md` (also served as `/vlc.html`).
- Pipeline for all 82 VFC parts: bilingual VI+ZH lines/SRT, daily phrases (food/shopping/work/survival first), rule-based tones + readings, verified original-audio clips. Counts: see `## Numbers`.
- New site: today/day view, 12-week plan (week 1 = tones, consonants, vowels, finals, address terms), part pages with phrase cards + full bilingual transcript + SRT download, SRS review, scenes, whole-show search, VLC page. Piper TTS replaced by original clips; device `speechSynthesis` only as labelled fallback.
- 5S Online + IT scenario archived at `/archive/5s-online/`.
- Cloudflare Access apps for `/private` on tv.alanzhu.dev and tv-preview.alanzhu.dev (owner Google login, reusing policy "Quota dashboard owner via Google").

## Numbers
See PR #1 description for the latest run (parts, lines, phrases, verified clips, GLM fallback parts).

## Next
- Alan acceptance on preview, then production deploy (`npx wrangler deploy`).
- Work/factory topic pack (tăng ca, nghỉ phép, hàng lỗi, ca đêm…): search corpus for originals; fallback labelled TTS.
- Optional quality pass: merge YouTube ASR + Whisper hypotheses; proofread week-1/2 parts.
- Progress is per-browser (localStorage); add export/import if Alan uses two devices.
