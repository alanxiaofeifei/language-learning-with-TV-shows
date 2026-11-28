// Short (12 weeks / 84 days) and long-track outlines for the generic shows.
// Everything here is our own teaching text; no show lines. Day plans are generated
// deterministically from the episode count, with more close-study days for shorter shows.

export const SHORT_DAYS = 84;
export const SHORT_WEEKS_N = 12;

// Day 1 = orientation; every 7th day = review; all other days carry episodes.
export function isReviewDay(day) { return day % 7 === 0; }

export function buildShowDays(epCount) {
  if (!Number.isInteger(epCount) || epCount < 1) throw new Error("epCount must be a positive integer");
  const slots = [];
  for (let d = 2; d <= SHORT_DAYS; d++) if (!isReviewDay(d)) slots.push(d);
  const S = slots.length;                       // 71
  const byDay = new Map();
  let prev = 0;
  slots.forEach((day, s) => {
    if (epCount >= S) {
      const from = Math.floor((s * epCount) / S) + 1, to = Math.floor(((s + 1) * epCount) / S);
      const eps = []; for (let e = from; e <= to; e++) eps.push(e);
      byDay.set(day, { kind: "watch", eps });
      prev = to;
    } else {
      const e = Math.floor((s * epCount) / S) + 1;
      byDay.set(day, { kind: e !== prev ? "watch" : "deep", eps: [e] });
      prev = e;
    }
  });
  const days = [];
  for (let day = 1; day <= SHORT_DAYS; day++) {
    const week = Math.ceil(day / 7);
    if (day === 1) days.push({ day, week, kind: "intro", eps: [] });
    else if (isReviewDay(day)) {
      const watched = days.filter((d) => d.week === week && d.kind === "watch").flatMap((d) => d.eps);
      days.push({ day, week, kind: "review", eps: watched });
    } else days.push({ day, week, ...byDay.get(day) });
  }
  return days;
}

export function watchDays(days) {
  return days.filter((d) => d.kind === "watch");
}

export function nextShowDay(days, doneDays) {
  return days.find((d) => !doneDays.includes(d.day)) || days[days.length - 1];
}

// Weekly focus per target language, written for both UI languages.
export const SHORT_WEEKS = {
  zh: [
    { zh: ["上手与听感", "适应原速普通话：先开中文 + 越南语字幕，标出听不清的词。"], vi: ["Làm quen và nghe", "Quen với tiếng Phổ thông tốc độ thật: bật phụ đề Trung + Việt, đánh dấu từ nghe không rõ."] },
    { zh: ["家庭称谓", "爸、妈、哥、嫂、老三；称呼里的亲疏和辈分。"], vi: ["Xưng hô trong gia đình", "Bố, mẹ, anh, chị dâu, con út; xưng hô thể hiện thân sơ và vai vế."] },
    { zh: ["语气词与反问", "吧、呢、嘛、啊；“你说呢”“不是……吗”这类反问。"], vi: ["Trợ từ ngữ khí và câu hỏi tu từ", "吧, 呢, 嘛, 啊; câu hỏi tu từ kiểu “你说呢”, “不是……吗”."] },
    { zh: ["结果补语与可能补语", "V得了 / V不了、V完、V好、V住，听剧里的用法。"], vi: ["Bổ ngữ kết quả và khả năng", "V得了 / V不了, V完, V好, V住 — nghe cách dùng trong phim."] },
    { zh: ["把字句与被字句", "家务、钱、房子：谁对什么做了什么。"], vi: ["Câu chữ 把 và 被", "Việc nhà, tiền, nhà cửa: ai làm gì với cái gì."] },
    { zh: ["吵架与劝和", "抱怨、顶嘴、打圆场、道歉；注意分寸。"], vi: ["Cãi nhau và hòa giải", "Phàn nàn, cãi lại, giảng hòa, xin lỗi; chú ý mức độ."] },
    { zh: ["职场与商务", "公司、客户、项目、升职；正式和口语怎么切换。"], vi: ["Công sở và kinh doanh", "Công ty, khách hàng, dự án, thăng chức; chuyển giữa trang trọng và khẩu ngữ."] },
    { zh: ["成语与俗语", "剧中常见四字词，按 HSK 5–6 标准积累。第二遍关越南语字幕。"], vi: ["Thành ngữ và tục ngữ", "Thành ngữ bốn chữ hay gặp, tích lũy theo chuẩn HSK 5–6. Lần xem thứ hai tắt phụ đề Việt."] },
    { zh: ["钱与房子", "彩礼、房产、借钱、养老：数字和金额听写。"], vi: ["Tiền và nhà", "Sính lễ, nhà đất, vay tiền, dưỡng lão: nghe chép số và số tiền."] },
    { zh: ["情绪与心理", "委屈、心寒、想开；形容情绪的近义词辨析。"], vi: ["Cảm xúc và tâm lý", "Tủi thân, lạnh lòng, nghĩ thoáng; phân biệt từ gần nghĩa chỉ cảm xúc."] },
    { zh: ["只看中文字幕", "关掉越南语，只留中文；卡壳再开拼音。"], vi: ["Chỉ phụ đề tiếng Trung", "Tắt tiếng Việt, chỉ giữ tiếng Trung; vướng mới bật pinyin."] },
    { zh: ["总复习与 HSK 自测", "复习卡清零；用本剧词表做一次 HSK 风格的听力和阅读自测。"], vi: ["Ôn tập và tự kiểm tra HSK", "Ôn hết thẻ; tự kiểm tra nghe và đọc kiểu HSK bằng từ vựng của phim."] },
  ],
  en: [
    { zh: ["上手与听感", "先开英文 + 中文字幕，习惯美式语速和笑点节奏。"], vi: ["Làm quen và nghe", "Bật phụ đề Anh + Việt, quen với tốc độ nói kiểu Mỹ và nhịp hài."] },
    { zh: ["缩读与连读", "gonna / wanna / gotta、弱读的 to / and / of。"], vi: ["Nói tắt và nối âm", "gonna / wanna / gotta, đọc nhẹ to / and / of."] },
    { zh: ["打招呼与闲聊", "How you doin'、What's up、small talk 的接话方式。"], vi: ["Chào hỏi và nói chuyện phiếm", "How you doin', What's up, cách tiếp lời khi small talk."] },
    { zh: ["短语动词 I", "go out with、break up、hang out、figure out。"], vi: ["Cụm động từ I", "go out with, break up, hang out, figure out."] },
    { zh: ["约会与感情", "ask out、be into someone、move on。"], vi: ["Hẹn hò và tình cảm", "ask out, be into someone, move on."] },
    { zh: ["反讽与夸张", "听出 sarcasm：语调和 “Oh, great” 这类反话。"], vi: ["Mỉa mai và phóng đại", "Nhận ra sarcasm: ngữ điệu và câu nói ngược kiểu “Oh, great”."] },
    { zh: ["工作与钱", "job、boss、rent、tip；练习谈工作、房租和小费。"], vi: ["Công việc và tiền", "job, boss, rent, tip; luyện nói về công việc, tiền thuê nhà và tiền boa."] },
    { zh: ["短语动词 II 与习语", "第二遍关中文字幕，只在卡壳时打开。"], vi: ["Cụm động từ II và thành ngữ", "Lần xem thứ hai tắt phụ đề Việt/Trung, chỉ bật khi vướng."] },
    { zh: ["请求、拒绝与道歉", "Could you…、I'd rather not…、My bad。"], vi: ["Nhờ vả, từ chối, xin lỗi", "Could you…, I'd rather not…, My bad."] },
    { zh: ["家人与朋友", "家庭聚会、节日、婚礼里的常用表达。"], vi: ["Gia đình và bạn bè", "Cách nói thường gặp khi họp mặt gia đình, ngày lễ, đám cưới."] },
    { zh: ["只看英文字幕", "关掉中文 / 越南语，只留英文。"], vi: ["Chỉ phụ đề tiếng Anh", "Tắt tiếng Trung / tiếng Việt, chỉ giữ tiếng Anh."] },
    { zh: ["总复习与自测", "复习卡清零；挑 3 集无字幕看，写下听懂的梗。"], vi: ["Ôn tập và tự kiểm tra", "Ôn hết thẻ; chọn 3 tập xem không phụ đề, ghi lại các câu đùa hiểu được."] },
  ],
};

// Long-track outlines: short, human-readable stages. Available shows link to their short tracks.
export const LONG_OUTLINES = {
  zh: [
    { show: "都挺好", status: "now", span: { zh: "第 1 年", vi: "Năm 1" },
      goal: { zh: "家庭剧打底：日常口语、称谓、吵架与和解；HSK 4–5 词汇在语境里吃透。", vi: "Nền tảng bằng phim gia đình: khẩu ngữ hằng ngày, xưng hô, cãi vã và làm hòa; nắm chắc từ vựng HSK 4–5 trong ngữ cảnh." } },
    { show: "欢乐颂 1", status: "planned", span: { zh: "第 2 年", vi: "Năm 2" },
      goal: { zh: "都市职场与合租：职场用语、会议、谈判；向 HSK 6 推进。", vi: "Công sở đô thị và ở ghép: từ ngữ công sở, họp, đàm phán; tiến tới HSK 6." } },
    { show: "我们与恶的距离", status: "planned", span: { zh: "第 3 年 · 台湾模块", vi: "Năm 3 · học phần Đài Loan" },
      goal: { zh: "台湾国语与用语差异、繁体字阅读、新闻和社会议题词汇；HSK 7–9 方向。", vi: "Tiếng Quốc ngữ Đài Loan và khác biệt từ ngữ, đọc chữ phồn thể, từ vựng tin tức và vấn đề xã hội; hướng HSK 7–9." } },
  ],
  en: [
    { show: "Friends", showId: "friends", status: "now", span: { zh: "第 1 年 · 核心课程", vi: "Năm 1 · chương trình chính" },
      goal: { zh: "日常美式口语打底：缩读、短语动词、闲聊和约会话题。", vi: "Nền tảng khẩu ngữ Mỹ hằng ngày: nói tắt, cụm động từ, chuyện phiếm và hẹn hò." } },
    { show: "Seinfeld", showId: "seinfeld", status: "now", span: { zh: "第 2 年", vi: "Năm 2" },
      goal: { zh: "练习快节奏的日常对话，听懂吐槽和反讽。", vi: "Luyện hội thoại đời thường tốc độ nhanh, nghe hiểu lời châm biếm và mỉa mai." } },
    { show: "Desperate Housewives", showId: "desperate-housewives", status: "now", span: { zh: "第 3 年", vi: "Năm 3" },
      goal: { zh: "学习郊区生活用语，练习理解叙事旁白。", vi: "Học từ ngữ về đời sống ngoại ô và luyện hiểu lời dẫn truyện." } },
    { show: "Silicon Valley", showId: "silicon-valley", status: "now", span: { zh: "第 3 年 · 科技职场模块", vi: "Năm 3 · học phần công nghệ" },
      goal: { zh: "聚焦 2020 年前的现代科技与创业词汇，涵盖软件工程、产品和融资。", vi: "Tập trung vào từ vựng công nghệ hiện đại và khởi nghiệp trước năm 2020, gồm kỹ thuật phần mềm, sản phẩm và gọi vốn." } },
  ],
};
