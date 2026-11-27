# STATUS

Updated 2026-11-28 06:28 (Asia/Saigon, UTC+7).

## Done
- Site is now a language picker at `#/`. Vietnamese (北越) is the only ready language: 《Về nhà đi con》回家吧，孩子, with a **12-week short track** (existing 84-day plan, `vndc:v1` progress kept) and a **5-year long track** (260 weeks, 6 stages: 立足 → 日常自如 → 社交与分寸 → 职场沟通 / Chilisin 工厂 IT → 接近母语听力 → 循环保持). Same 82 parts / 28,900 lines / 1,239 phrases / 419 clips.
- Placeholder language pages (“即将推出 / 剧集待选”) for 英语（美式）, 法语（加拿大）, 日语（东京标准音）, 西班牙语（美式/拉美）, 粤语（香港）. Catalog and hash routes in `site/lib/catalog.js` are built so a later language + show can be added without rewriting the shell. Legacy hashes (`#/plan`, `#/day/N`, …) still open the Vietnamese short track.
- UI refresh (warm paper, display serif, language/track cards) plus interactive motion: phrase-card flip/reveal, page transitions, progress-bar animation, hover tilt, scroll progress. `prefers-reduced-motion` turns all of that off. No heavy animation libraries; MotionHarness techniques only, not a copy of motionharness.top.
- Private assets still Worker static files behind Access (not in Git). Access apps and policies were not changed. `npm test`: 15/15 passed.
- Independent pre-deploy review: Antigravity CLI `agy --mode plan --model gemini-4-argon-high` (no quota rotation needed). Verdict was request-changes; blockers and majors were fixed before deploy (swapMain `fill:forwards` hiding `<main>`, flip-card keyboard/`inert`, track-switcher `aria-current`, 404 `ctx` pollution, cross-track SRS due cards, reveal-delay cap, in-page rerenders without full-page transitions). Supporting long-track text was authored in-repo; DeepSeek/GLM spend this pass: **US$0**.

## Numbers
- Parts: 82 (P06 via Whisper; the other 81 from YouTube auto captions).
- Subtitle / transcript lines: 28,900.
- Phrases: 1,239.
- Verified original-audio clips: **419**. Parts with no verified clip: P04, P07, P46.
- Short track: 12 weeks, 84 days, each part once.
- Long track: 260 weeks; first-pass deep weeks cover P01–P82 once; year 5 cycles the whole show.
- Earlier LLM pipeline (unchanged): 1,368 DeepSeek `deepseek-chat` calls, 0 GLM; about US$1.25 off-peak.

## Preview
- URL: https://tv-preview.alanzhu.dev/
- Redeployed 2026-11-28 06:28 UTC+7 with the language home, two Vietnamese tracks, and motion upgrade. Worker `language-learning-with-tv-shows-preview`. Version ID: `0cea8dfa-e242-4d18-ac38-460b82d69bae`. Uploaded 6 new public files; 419 clips already on the Worker were reused.
- Anonymous checks (browser User-Agent): `/` → 200 (title 看剧学语言, cache MISS); `/app.js`, `/lib/catalog.js`, `/lib/long-curriculum.js`, `/styles.css` → 200; `/private`, `/private/`, `/private/data/index.json` → 302 to `alaninsights.cloudflareaccess.com` (preview Access AUD).

## Stages
| Stage | State |
| --- | --- |
| Local commit | pending this STATUS + feature files |
| Pushed to `plan/ve-nha-di-con` | pending |
| Merged | no (draft PR #1; Alan authorized merge after this work) |
| Preview deployed | done — 06:28 UTC+7, version `0cea8dfa-e242-4d18-ac38-460b82d69bae` |
| Preview verified | done — anonymous `/` 200 and `/private` 302 |
| Production deployed | not yet (next, after merge) |

## Next
- Merge PR #1 and deploy production (`npx wrangler deploy`, default env only) with the same local `site/private` tree; verify `tv.alanzhu.dev` `/` 200 and `/private` 302 to the existing “TV study private” Access app.
- When Alan picks shows for the other languages, add a show record in `catalog.js` and run the pipeline into that show’s private data prefix.
- Optional quality pass on P04, P07, P46 (no verified clips); export/import of per-browser progress.
