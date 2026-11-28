# STATUS

Updated 2026-11-28 12:00 (Asia/Saigon, UTC+7).

## Multi-language pilot (feat/multilang-pilot)
- Ready languages: Vietnamese (回家吧，孩子), Chinese 《都挺好》 (official 正午阳光 YouTube, 46 eps: zh/pinyin/vi/en lines, 658 phrases with original-audio clips, bilingual SRTs) and English 《Friends》 S01–S02 (text mode: 48 eps, zh+vi translations, 691 phrases, no audio; timings are approximate). fr/ja/es/yue stay placeholders with planned picks.
- Access: separate policy "TV study: Alan + Linh via Google" on both TV Access apps (quota dashboard policy untouched).
- Worker `/private/me.json` gives per-user display defaults from secret `USER_PREFS` (display only, not authorization); Linh's profile defaults to zh+en with a Vietnamese UI.
- Review: Antigravity agy plan mode found 0 blockers in the final pass; earlier 4 major/15 minor fixed. DeepSeek translation/phrases only (no GLM).
- Prepared, not shipped: `pipeline/multi/fetch_tvsubtitles.py` plus Seinfeld and Silicon Valley configs (S1 SRTs fetched locally).


## Done
- Site is now a language picker at `#/`. Vietnamese (北越) is the only ready language: 《Về nhà đi con》回家吧，孩子, with a **12-week short track** (existing 84-day plan, `vndc:v1` progress kept) and a **5-year long track** (260 weeks, 6 stages: 立足 → 日常自如 → 社交与分寸 → 职场沟通 / Chilisin 工厂 IT → 接近母语听力 → 循环保持). Same 82 parts / 28,900 lines / 1,239 phrases / 419 clips.
- Placeholder language pages (“即将推出 / 剧集待选”) for 英语（美式）, 法语（加拿大）, 日语（东京标准音）, 西班牙语（美式/拉美）, 粤语（香港）. Catalog and hash routes in `site/lib/catalog.js` are built so a later language + show can be added without rewriting the shell. Legacy hashes (`#/plan`, `#/day/N`, …) still open the Vietnamese short track.
- UI refresh (warm paper, display serif, language/track cards) plus interactive motion: phrase-card flip/reveal, page transitions, progress-bar animation, hover tilt, scroll progress. `prefers-reduced-motion` turns all of that off. No heavy animation libraries; MotionHarness techniques only, not a copy of motionharness.top.
- Private assets are Worker static files behind Access (not in Git). Access apps and policies were not changed. `npm test`: 15/15 passed.
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
- Worker `language-learning-with-tv-shows-preview`. Version ID: `0cea8dfa-e242-4d18-ac38-460b82d69bae` (2026-11-28 06:28 UTC+7).
- Anonymous checks: `/` → 200 (title 看剧学语言); `/app.js`, `/lib/catalog.js`, `/styles.css` → 200; `/private` and `/private/data/index.json` → 302 to `alaninsights.cloudflareaccess.com` (preview Access AUD).

## Production
- URL: https://tv.alanzhu.dev/
- Worker `language-learning-with-tv-shows`. Version ID: `5be4defe-3578-4833-92dd-a264a4b650cb` (2026-11-28 06:30 UTC+7). Uploaded 629 new or modified assets, including the 419-clip `site/private` tree (production had been the pre-rebuild site). ACCESS_AUD is the existing “TV study private” app.
- Anonymous checks (browser User-Agent): `/` → 200 (title 看剧学语言, description lists the placeholder languages); `/app.js`, `/lib/catalog.js`, `/styles.css` → 200; `/private`, `/private/`, `/private/data/index.json` → 302 to `alaninsights.cloudflareaccess.com/cdn-cgi/access/login/tv.alanzhu.dev` with production Access AUD `7ced6fd4…`.

## Stages
| Stage | State |
| --- | --- |
| Local commit | done (`d77b384666b57cdb0b64b0cc792a150e93c03077`) |
| Pushed to `plan/ve-nha-di-con` | done |
| Merged | done — PR #1 merge commit `00fce0dc354c33fcb80aeae8ca5182ca03ad0323` (06:29 UTC+7) |
| Preview deployed | done — version `0cea8dfa-e242-4d18-ac38-460b82d69bae` |
| Preview verified | done — anonymous `/` 200 and `/private` 302 |
| Production deployed | done — version `5be4defe-3578-4833-92dd-a264a4b650cb` |
| Production verified | done — anonymous `/` 200 and `/private` 302 to “TV study private” |

## Next
- When Alan picks shows for the other languages, add a show record in `catalog.js` and run the pipeline into that show’s private data prefix.
- Optional quality pass on P04, P07, P46 (no verified clips); export/import of per-browser progress.

## Deploy record (2026-11-28)
- Preview `b8893249-847e-4300-9a94-69b90e250fa5`, production `c62cf161-d39f-4403-b94c-6baa08d88a81` (main 8a62627). `USER_PREFS` secret set on both workers. Anonymous `/` 200; `/private`, `/private/me.json`, `/private/shows/*` → 302 Access login. Owner/Linh logged-in views not testable from the box.
