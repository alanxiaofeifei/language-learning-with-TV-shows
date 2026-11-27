# 用 VLC 看《Về nhà đi con》越中双语字幕

字幕时间轴对应 **VFC Official** 频道的上传版本（播放列表 `PLdilN7V0FSOGDiPmg4MVIjP9dfLm0qxWA`，按剧情顺序编为 P01–P82，见 `data/ve-nha-di-con/parts.json`）。从别的频道下载的版本剪辑不同，时间会对不上。

每条字幕两行：上面越南语（已按语义断句、修正大部分自动识别错误），下面简体中文。文件为 UTF-8（带 BOM），Windows 和 macOS 的 VLC 都能直接识别。

## 1. 放好文件（推荐：同名自动加载）

1. 新建一个文件夹，例如 `D:\Vietnamese\VeNhaDiCon\`。
2. 视频和字幕放在同一个文件夹，**文件名只差扩展名**：
   ```
   VeNhaDiCon_P01_08B-aPzkLAg.mp4
   VeNhaDiCon_P01_08B-aPzkLAg.srt
   ```
3. 用 VLC 打开视频，字幕会自动出现。没出现就按第 2 步手动加。

## 2. 手动加载字幕

- **Windows**：播放视频 → 菜单 **字幕 (Subtitle) → 添加字幕文件 (Add Subtitle File…)** → 选 `.srt`。
- **macOS**：播放视频 → 菜单 **字幕 (Subtitles) → 添加字幕文件… (Add Subtitle File…)**。
- 两个系统都可以直接把 `.srt` **拖进正在播放的 VLC 窗口**。
- 有多条字幕时：**字幕 → 子轨道 (Sub Track)** 选当前这条。

## 3. 字体与大小（越南语声调符号 + 中文都要能显示）

1. **Windows**：工具 (Tools) → 偏好设置 (Preferences) → **字幕/OSD (Subtitles/OSD)**；**macOS**：VLC → 设置 (Settings) → **字幕 (Subtitles)**。
2. 字体选同时包含越南语和中文的：Windows 用 **Microsoft YaHei**（微软雅黑）或 **Noto Sans CJK SC**；macOS 用 **PingFang SC** 或 **Noto Sans CJK SC**。看到方框或声调符号错位，就换另一款。
3. 字号建议选「大 (Large)」，勾选背景/描边方便看清。
4. 默认编码 (Default encoding) 选 **Universal (UTF-8)**。
5. 保存后**重启 VLC** 生效。

## 4. 学习时最常用的操作

| 操作 | Windows | macOS |
|---|---|---|
| 暂停 / 继续 | 空格 | 空格 |
| 后退 3 秒（重听一句） | Shift + ← | ⌘ + ⌃ + ← |
| 字幕提前 / 延后 50 ms（对不上时） | G / H | G / H |
| 放慢 / 恢复播放速度 | `[` / `=` | 播放 (Playback) → 播放速度 |
| 单句循环 (A-B) | 视图 → 高级控制，点 A-B 按钮两次 | 播放 → A→B 循环 |
| 关字幕（只听不看） | 字幕 → 子轨道 → 禁用 | 同左 |

## 5. 建议的每日看法（约 45 分钟）

1. 先在网站看当天这一集的 10–15 个「日常用语」，听原声片段，跟读 3 遍。
2. VLC 打开双语字幕看一遍全集，听到卡片里的句子时暂停，跟读。
3. 第二遍（或只挑 5 分钟片段）关掉字幕只听，检验能听出几个词块。
4. 回网站做复习打分，系统安排明天要复习的卡片。
