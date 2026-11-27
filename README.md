# 看剧学语言

用电视剧的原声学口语。首页按语言分类：

- **越南语（北越）**已开放《Về nhà đi con》（回家吧，孩子）：同一 82 段有 **12 周短期版** 和约 **5 年长期精读版**（生存句 → 工厂职场沟通 → 接近母语听力）。
- 英语（美式）、法语（加拿大）、日语（东京标准音）、西班牙语（美式/拉美）、粤语（香港）先占位，剧集待选。

在线：[tv.alanzhu.dev](https://tv.alanzhu.dev)。台词、字幕和原声片段受版权保护，只在登录后（Cloudflare Access）可见，不进 Git。

- 计划与数据管线：[docs/PLAN-ve-nha-di-con.md](docs/PLAN-ve-nha-di-con.md)
- VLC 双语字幕步骤：[docs/VLC-bilingual-subtitles.md](docs/VLC-bilingual-subtitles.md)
- 开发约定：[AGENTS.md](AGENTS.md) · 进度：[docs/STATUS.md](docs/STATUS.md)
- 旧内容（5S Online、IT 场景）：`site/archive/5s-online/`

```sh
npm ci && npm test
npx wrangler deploy --env preview   # 预览站 tv-preview.alanzhu.dev
```
