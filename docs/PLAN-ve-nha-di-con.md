# 重建计划：用《Về nhà đi con》（回家吧，孩子）3 个月入门北越语

状态：Phase 1（调研 + 方案 + 原型脚本）。生产站 tv.alanzhu.dev 未改动。

## 0. 目标与约束

- 学习者：越南语零基础、汉语母语、英语好；在海防 Chilisin 上班，必须学**北越（河内）口音**。
- 3 个月目标：能应付吃饭、买东西、问路、打车，以及工作中的寒暄、请假、听懂简单指令；能听出剧中高频日常句。
- 痛点：YouTube 自动翻译慢、不准；看不懂也读不出越南语文字；现有 TTS 声音怪。
- 方案原则：原剧原声 + 准确的双语字幕 + 每集精选日常用语（带时间戳、原声片段、读法、声调）+ 间隔重复复习。

## 1. 现状（main@f1dd928，2026-11-24）

- 纯静态站，Cloudflare Workers Static Assets（`wrangler.jsonc`，`assets.directory=./site`，自定义域 tv.alanzhu.dev），无后端、无构建步骤。
- 剧目仍是《5S Online》第一季前 5 集（不是《Về nhà đi con》）：`site/episodes.js` 每集 6 张三语卡（vi/zh/en + 声调提示 + 例句）和 1 条「原剧听辨」时间点。
- 音频：`scripts/build-episode-audio.py` 用 Piper TTS（CakeByVPBank 北部女声）生成 `site/audio/<id>/<n>.mp3`，即 Alan 说的「怪声音」。
- 导入台词：`site/import-subtitles.js` 解析 srt/vtt/txt，存在浏览器 localStorage；进度也只在 localStorage。
- 测试：`node --test`，仅覆盖字幕解析。没有 AGENTS.md / docs/STATUS.md。

## 2. 剧集与字幕来源调研（2026-11-27）

| 来源 | 内容 | 字幕 | 结论 |
|---|---|---|---|
| **VFC Official**（出品方 越南电视剧中心）[播放列表](https://www.youtube.com/playlist?list=PLdilN7V0FSOGDiPmg4MVIjP9dfLm0qxWA) | 82 段 × 约 30 分钟，共 42.7 小时，覆盖全剧（列表倒序，已反转为剧情顺序 P01–P82） | 81/82 有越南语**自动**字幕（带逐词时间）；0 条人工字幕；P06 无字幕 | **采用为主来源** |
| VTV Go 2019 原播 [列表](https://www.youtube.com/playlist?list=PLm8YCCTGZf4Uldo_6mjcEy22gBNPFC59J) | 按原集号「TẬP N」，85 集里能看到 70 集，15 集已下架 | 无任何字幕 | 只用于对照原集号 |
| VTV Go 2025 重剪 [列表](https://www.youtube.com/playlist?list=PLm8YCCTGZf4U3LeojHDSHA-yMVRi_JyIn) | #1–#57 + 番外，约 35 分钟/段 | 有自动字幕 | 不完整，作为备用 |
| VTV Giải Trí 英文标题片段 | 5–16 分钟剪辑 | 无人工英/中字幕 | 不用 |
| 字幕站（OpenSubtitles 等）、B 站、中文资源站 | 搜不到本剧的 SRT 或中字 | — | 无可用来源 |
| 越南「vietsub」在线站 | 盗版流媒体，越南剧本身没有外挂字幕 | — | 不使用 |

剧集事实：VTV1 2019-04-08 至 2019-08-12 首播，正片 85 集 + 番外 5 集；导演 Nguyễn Danh Dũng；中文译名《回家吧，孩子》/《孩子，回家吧！》。

自动字幕质量：河内口语识别大体可用，但有系统性错误（北音 d/gi/r 都读 /z/，导致 giỗ→dỗ、gần gũi→gần cũi，đường mật→đường mặt），且是滚动字幕，句子被切碎。全剧约 27.5 万个越南语词。

## 3. 数据管线

```
yt-dlp 自动字幕 json3（逐词时间）
  └─ ① 断句 + 纠错 + 中译（LLM，按 220 词分块，带上文与人物/称谓表）   pipeline/captions_to_bilingual.py
       └─ lines.json：{s,e,vi,zh,startMs,endMs}
            ├─ ② 双语 SRT（越上中下，UTF-8 BOM，无重叠）               同上
            ├─ ③ 每集 10–15 条日常用语（含时间戳和 YouTube &t= 跳转）    pipeline/extract_phrases.py
            │     └─ 声调标注由规则从变音符号算出（不靠 LLM）            pipeline/tones.py
            ├─ ④ 原声片段：yt-dlp 只取音频 → ffmpeg 按逐词时间裁剪（前留 0.3s、后留 0.5s，响度归一）
            └─ ⑤ 全剧检索：任意词块 → 所有出现位置 + 原声
```

- **P06 无字幕**：用 box 上的 faster-whisper large-v3-turbo（CPU，实测约 6 倍实时，一集约 5 分钟）补识别。
- **提高准确率（Phase 2 可选）**：把 YouTube 识别和 Whisper 识别两份结果同时交给 LLM 合并纠错；全剧 Whisper 约 7 小时 CPU，免费。
- **读法**：中国人友好读法改为规则生成（北音对照表：d/gi/r→z，tr→ch，s→x，x→s，nh→ny，ng/ngh，词尾 c/t/p 不爆破，元音 ơ/ư/â 的近似音），LLM 只写用法说明。原型里 LLM 写的读法质量一般，所以要换。
- **英文 gloss**：只给卡片，不进字幕（避免三行太挤）。

### 翻译引擎

- 已有并实测可用：**DeepSeek `deepseek-chat`**（每集约 15 次调用、约 75 秒，全剧估计约 2 美元，用现有余额，不需要升级）。中文自然，称谓偶尔判断错。
- GLM `glm-4-flash` 可用但质量明显差；Workers AI 免费额度作最后兜底。
- 不用 OpenAI。

### 原型样例（P01 自动生成，未人工校对）

```
00:00:10,970 --> 00:00:14,740
Lúc còn sống, con bé chỉ thích ăn miến.
她活着的时候，就爱吃粉丝。

00:00:52,850 --> 00:00:55,660
Dương đâu? Sao giờ này vẫn chưa thấy nó về ông ơi?
阿阳呢？这都几点了还没见她回来？
```

P01 产出：3,280 词 → 396 条双语字幕，无时间重叠；精选 15 条日常用语，例如 *Còn gì nữa không?*（还有别的吗？点菜买东西用）、*Yên tâm đi*（放心吧）、*Em xin lỗi ạ*（对不起，礼貌）、*Không sao đâu*（没事的）、*Anh đi tí anh về*（我去一下就回来）。

## 4. 网站改版（Phase 2–3）

- 首页改为《Về nhà đi con》课程目录，按 12 周排；保留 5S Online 和 IT 场景作为旧内容入口。
- 每集页：① 今日日常用语卡（原声片段、慢放、声调、读法、用法、跳转 YouTube 对应秒数）；② 双语全文（点任意句跳到 YouTube 对应时间）；③ 下载本集双语 SRT；④ 看完打卡。
- 复习：本地 FSRS 间隔重复（「忘了/难/会/简单」四档），每天上限 20 新卡 + 到期复习；进度仍存 localStorage，可导出备份。
- 声调与发音训练模块（第 1–2 周）：6 个声调用剧中原声的最小对立词，配声调曲线。
- 「生活/工作」专题包：剧里不会出现工厂用语，所以单独编吃饭、购物、打车、问路，以及上班常用的 tăng ca（加班）、nghỉ phép（请假）、hàng lỗi（不良品）、ca sáng/ca đêm（早/夜班）等；优先用全剧检索找原声，找不到再用真人读或 TTS 兜底，并标明是合成音。
- 移除 Piper TTS 卡片音频（剧集卡全部换原声）。
- 数据格式：`data/ve-nha-di-con/parts.json`（已提交：82 段的 videoId、时长、字幕情况），每集一份 `lines`/`phrases` JSON，由构建脚本生成 `site/` 下静态文件。

## 5. 12 周课程

| 周 | 重点 | 每天 |
|---|---|---|
| 1 | 北音发音：6 声调、难辨辅音（d/gi/r=z，tr/ch，s/x）、元音 ơ ư â ă、词尾 c/t/p/ng/nh；称谓体系（anh/chị/em/bố/mẹ/ông/bà） | 20 分钟发音 + P01 前 10 分钟 + 10 条生存句 |
| 2 | 生存句：打招呼、谢谢、对不起、多少钱、要这个、不要辣、买单 | P01–P03 片段，跟读原声 |
| 3–4 | 一天一段（P01→P14），双语字幕；专题：吃饭点菜、市场砍价 | 45 分钟（见 VLC 指南第 5 节） |
| 5–6 | P15→P28；专题：问路打车、电话用语 | 同上 + 复习 |
| 7–8 | P29→P42；专题：职场寒暄、请假、加班、汇报问题 | 同上；第 8 周起第二遍关字幕 |
| 9–10 | P43→P60；专题：工厂用语、听懂指令 | 同上 |
| 11–12 | P61→P82（一天约 1.5 段，可只看精选片段）；总复习 | 看越语字幕或无字幕 |

约 1,000–1,200 条剧中日常用语 + 约 300 条生活/工作专题句。每周日做一次 15 分钟自测（听原声选意思、看中文说越南语）。

## 6. 版权与隐私（需要 Alan 决定）

- 仓库和网站都是**公开**的。全集台词、双语 SRT 和原声片段都来自受版权保护的剧集，仅限个人学习。
- 建议：
  - 公开：剧集目录（videoId、时长、YouTube 链接）、代码、声调规则、单句示例。
  - **私有**：全集双语 SRT、每集台词全文、原声片段 → 放在 tv.alanzhu.dev 的 `/private/*`，前面加 Cloudflare Access（仅 Alan 的邮箱），或放到 R2 由 Worker 校验 Access 身份后返回；Git 里不提交这些文件（`work/` 已加入 .gitignore）。
  - 原声片段每条 ≤ 6 秒，只截取日常用语所在的那句。
- 备选：全部只在本地（box 生成，发给 Alan 自己的电脑），网站只做跳转 YouTube。

## 7. 下一步

- Phase 2：跑完 82 段双语 SRT（P06 用 Whisper 补）+ 每集用语 + 原声片段；先给 Alan 发 P01–P03 的 SRT 实测 VLC。
- Phase 3：网站改版 + FSRS 复习 + 发音周模块；私有资源按 Alan 的决定配置后再部署。
