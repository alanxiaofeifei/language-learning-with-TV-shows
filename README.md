# 看剧学语言

先听音辨认，再看完整一集，最后回来复习。首页是原有的越南语 IT 排障场景。影视学习从《5S Online》第一季前 5 集开始，每集 6 张越南语、简体中文和英文对照卡，配逐音节声调和慢速朗读。

在线学习入口为 [tv.alanzhu.dev](https://tv.alanzhu.dev)。

## 学习

- **预习**。听词块、辨认声调，想想意思，再展开英中释义与例句。
- **看剧**。打开原片，在视频简介中选择「显示文字稿」。越南语 CC 由 YouTube 自动识别，英中字幕可用播放器的自动翻译。看完回来标记观看。
- **复习**。再练一次已学词块。预习、观看、复习全完成后，目录会标记该集已完成。进度跟随当前浏览器与网址。
- **导入台词**。粘贴台词或选择 `.srt`、`.vtt`、`.txt`。可附影片网址用于回听时间点。文本保留在当前浏览器，默认用前 10 条练习，全文可展开查看。设备提供相应的语音时，可试听导入原句。

三语卡是围绕每集主题编写的学习例句。「原剧听辨」收录一个在该集自动字幕中核实的词块，可跳到字幕段起点回听。完整对白和自动字幕可在发布者的播放页查看。 [第一季播放列表](https://www.youtube.com/playlist?list=PL3m_2IMNSXxcd1Ff3_Czw8je8BvHUpK6C) · [YouTube 文字稿说明](https://support.google.com/youtube/answer/15930243)

## 本地开发

```sh
npm ci
npm test
npm run preview
```

网站文件位于 `site/`。追加剧集时更新 `site/episodes.js`，使用固定 ID（如 `s01e06`）。已上线剧集的 ID 和卡片顺序应保持稳定，已有进度按这两个值记录。生成新音频需要 Python、Node.js、FFmpeg 和 FFprobe。

```sh
python -m pip install piper-tts==1.8.0 huggingface_hub
python scripts/build-episode-audio.py
```

影视卡片音频采用 Cake by VPBank 的 Piper 越南语模型，使用其标注为北部女声的 Ngọc Lan 音色。模型权重由发布者以 MIT 许可发布，构建脚本固定使用已核验的模型版本。 [模型和音色说明](https://huggingface.co/CakeByVPBank/piper-pgl-v4-vi_VN-version39_epoch39/blob/8ea50134bea762f6a1faac671e1a33c41871289c/README.md#speakers--samples) · [Piper TTS](https://github.com/OHF-Voice/piper1-gpl) · [Piper Voices](https://github.com/rhasspy/piper-voices)

用有目标账户访问权限的 Wrangler 登录后，运行 `npm run deploy` 可部署到 Cloudflare 的自定义域名。
