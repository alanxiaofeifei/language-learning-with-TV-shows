# 看剧学越南语 · Về nhà đi con（回家吧，孩子）

用越南剧《Về nhà đi con》的原声学北越（河内）口语：每天一段剧，先学 10–15 条日常用语（原声片段、拼音读法、声调），再用 VLC 配越中双语字幕看全集，最后间隔复习。12 周排完 82 段。

在线：[tv.alanzhu.dev](https://tv.alanzhu.dev)。台词、字幕和原声片段受版权保护，只在登录后（Cloudflare Access）可见，不进 Git。

- 计划与数据管线：[docs/PLAN-ve-nha-di-con.md](docs/PLAN-ve-nha-di-con.md)
- VLC 双语字幕步骤：[docs/VLC-bilingual-subtitles.md](docs/VLC-bilingual-subtitles.md)
- 开发约定：[AGENTS.md](AGENTS.md) · 进度：[docs/STATUS.md](docs/STATUS.md)
- 旧内容（5S Online、IT 场景）：`site/archive/5s-online/`

```sh
npm ci && npm test
npx wrangler deploy --env preview   # 预览站 tv-preview.alanzhu.dev
```
