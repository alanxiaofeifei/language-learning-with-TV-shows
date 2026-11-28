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
  ja: [
    { zh: ["假名与汉字", "对照原文与假名，标出还不熟悉的读音。"], vi: ["Kana và kanji", "Đối chiếu nguyên văn với kana, đánh dấu cách đọc chưa quen."] },
    { zh: ["助词", "比较 は、が、を 在句子里的作用。"], vi: ["Trợ từ", "So sánh vai trò của は, が và を trong câu."] },
    { zh: ["礼貌体与普通体", "观察不同关系下如何切换说法。"], vi: ["Thể lịch sự và thể thường", "Quan sát cách đổi lối nói theo quan hệ giữa các nhân vật."] },
    { zh: ["请求", "整理 て 形和委婉请求的用法。"], vi: ["Nhờ vả", "Ghi lại cách dùng thể て và cách nhờ vả nhẹ nhàng."] },
    { zh: ["家务与分工", "用自己的话写一份家务分工。"], vi: ["Việc nhà và phân công", "Tự viết cách phân chia việc nhà."] },
    { zh: ["省略", "根据上下文补出省略的主语。"], vi: ["Lược bỏ", "Dựa vào ngữ cảnh để tìm chủ ngữ bị lược."] },
    { zh: ["职场", "区分同事之间的闲聊和正式用语。"], vi: ["Công sở", "Phân biệt lời trò chuyện giữa đồng nghiệp và cách nói trang trọng."] },
    { zh: ["理由与转折", "比较 から、ので、けど 的语气。"], vi: ["Lý do và chuyển ý", "So sánh sắc thái của から, ので và けど."] },
    { zh: ["推测", "用自己的例句练习表达不确定性。"], vi: ["Phỏng đoán", "Tự đặt câu để luyện cách diễn đạt sự không chắc chắn."] },
    { zh: ["道歉与回应", "按人物关系整理道歉和回应的表达。"], vi: ["Xin lỗi và đáp lời", "Nhóm cách xin lỗi và đáp lời theo quan hệ giữa các nhân vật."] },
    { zh: ["独立阅读", "先关掉假名和译文，遇到生词再打开。"], vi: ["Đọc độc lập", "Tắt kana và bản dịch, chỉ bật lại khi gặp từ khó."] },
    { zh: ["JLPT 复习", "按 JLPT 等级回顾卡片，并用重点句型造句。"], vi: ["Ôn theo JLPT", "Ôn thẻ theo cấp JLPT và đặt câu với mẫu câu chính."] },
  ],
  fr: [
    { zh: ["法国法语入门", "先对照原文和译文，标出常用表达。"], vi: ["Làm quen với tiếng Pháp ở Pháp", "Đối chiếu nguyên văn và bản dịch, đánh dấu các cách nói thường gặp."] },
    { zh: ["称呼", "观察人物何时用 tu，何时用 vous。"], vi: ["Xưng hô", "Quan sát khi nào nhân vật dùng tu và khi nào dùng vous."] },
    { zh: ["口语否定", "标出省略 ne 的句子，写出完整形式。"], vi: ["Phủ định trong khẩu ngữ", "Đánh dấu câu lược ne và viết lại dạng đầy đủ."] },
    { zh: ["提问", "比较口语问句和较正式的倒装问句。"], vi: ["Đặt câu hỏi", "So sánh câu hỏi khẩu ngữ với câu đảo ngữ trang trọng hơn."] },
    { zh: ["时间与叙事", "比较复合过去时和未完成过去时。"], vi: ["Thời gian và kể chuyện", "So sánh passé composé và imparfait."] },
    { zh: ["代词", "找出 le、lui、y、en 指代的对象。"], vi: ["Đại từ", "Tìm đối tượng mà le, lui, y và en thay thế."] },
    { zh: ["请求与指令", "把直接指令改写成委婉请求。"], vi: ["Yêu cầu và chỉ dẫn", "Viết lại mệnh lệnh trực tiếp thành lời nhờ lịch sự."] },
    { zh: ["语域", "比较熟人之间与正式场合的措辞。"], vi: ["Ngữ vực", "So sánh cách nói giữa người quen với cách nói trong tình huống trang trọng."] },
    { zh: ["描述与推测", "用自己的话描述人物知道什么、猜到什么。"], vi: ["Mô tả và suy đoán", "Dùng lời của mình để mô tả nhân vật biết gì và đoán gì."] },
    { zh: ["复述", "用连接词和时间词写一段简短复述。"], vi: ["Kể lại", "Viết đoạn kể lại ngắn, dùng từ nối và từ chỉ thời gian."] },
    { zh: ["只看法语", "关闭译文，读完一段后核对理解。"], vi: ["Chỉ đọc tiếng Pháp", "Tắt bản dịch, đọc một đoạn rồi đối chiếu cách hiểu."] },
    { zh: ["CEFR 复习", "按 CEFR 等级回顾卡片，为常用表达各写一个新例句。"], vi: ["Ôn theo CEFR", "Ôn thẻ theo cấp CEFR và đặt câu mới với các cách nói thông dụng."] },
  ],
  es: [
    { zh: ["墨西哥西语入门", "先开西语原文 + 中文，习惯语速；注意拉美的 seseo：z 以及 e、i 前的 c（cena、cielo、zapato）都读 /s/；a、o、u 前的 c 仍读 /k/（casa）。"], vi: ["Làm quen với tiếng Tây Ban Nha Mexico", "Bật nguyên văn tiếng Tây Ban Nha + bản dịch, quen tốc độ nói; để ý seseo ở Mỹ Latinh: z và c đứng trước e, i (cena, cielo, zapato) đều đọc là /s/; c đứng trước a, o, u vẫn đọc là /k/ (casa)."] },
    { zh: ["ser 与 estar", "身份、性质用 ser，状态、位置用 estar；把剧里的例子分成两栏。"], vi: ["ser và estar", "ser cho danh tính, bản chất; estar cho trạng thái, vị trí. Chia các ví dụ trong phim thành hai cột."] },
    { zh: ["称呼：tú、usted、ustedes", "观察人物何时用 tú，何时用 usted；拉美复数一律用 ustedes，不用 vosotros。"], vi: ["Xưng hô: tú, usted, ustedes", "Quan sát khi nào nhân vật dùng tú, khi nào dùng usted; ở Mỹ Latinh số nhiều luôn là ustedes, không dùng vosotros."] },
    { zh: ["常用不规则动词", "tener、ir、hacer、poder、querer 的现在时；用 ir a + 不定式说打算。"], vi: ["Động từ bất quy tắc thường gặp", "Thì hiện tại của tener, ir, hacer, poder, querer; dùng ir a + nguyên mẫu để nói dự định."] },
    { zh: ["pretérito 与 imperfecto", "一次完成的动作 vs 背景和习惯；把一段剧情用两种过去时复述。"], vi: ["pretérito và imperfecto", "Hành động xảy ra một lần so với bối cảnh và thói quen; kể lại một đoạn phim bằng hai thì quá khứ."] },
    { zh: ["墨西哥口语", "ahorita、¿mande?、órale、¿qué onda? 的意思和语气；ahorita 不一定是“马上”。"], vi: ["Khẩu ngữ Mexico", "Nghĩa và sắc thái của ahorita, ¿mande?, órale, ¿qué onda?; ahorita không hẳn là “ngay lập tức”."] },
    { zh: ["俚语与分寸", "güey、no manches、neta、chido、padre：哪些只在熟人之间说，哪些会显得粗鲁。"], vi: ["Tiếng lóng và chừng mực", "güey, no manches, neta, chido, padre: câu nào chỉ nói với người thân quen, câu nào nghe thô."] },
    { zh: ["宾语代词", "lo、la、le 和 se lo；代词放在变位动词前，或接在不定式、命令式后。"], vi: ["Đại từ tân ngữ", "lo, la, le và se lo; đại từ đứng trước động từ chia, hoặc gắn sau nguyên mẫu và mệnh lệnh."] },
    { zh: ["虚拟式入门", "quiero que…、ojalá…、para que…：愿望、请求和目的后面用虚拟式。"], vi: ["Làm quen với thức giả định", "quiero que…, ojalá…, para que…: sau mong muốn, yêu cầu và mục đích dùng thức giả định."] },
    { zh: ["家庭、钱与生意", "遗产、债务、合同、公司经营：练习数字、金额和日期的听写。"], vi: ["Gia đình, tiền bạc và kinh doanh", "Thừa kế, nợ nần, hợp đồng, điều hành công ty: luyện nghe chép số, số tiền và ngày tháng."] },
    { zh: ["情绪与戏剧冲突", "指责、辩解、道歉与和解，留意指小词 -ito / -ita 的语气；这一周关掉中文，只看西语。"], vi: ["Cảm xúc và xung đột kịch tính", "Trách móc, thanh minh, xin lỗi và làm hòa; để ý sắc thái của hậu tố giảm nhẹ -ito / -ita. Tuần này tắt bản dịch, chỉ đọc tiếng Tây Ban Nha."] },
    { zh: ["CEFR 复习与地区差异", "按 CEFR 等级回顾卡片；整理墨西哥和西班牙的用词差异，如 carro / coche、computadora / ordenador。"], vi: ["Ôn theo CEFR và khác biệt vùng miền", "Ôn thẻ theo cấp CEFR; ghi lại khác biệt từ ngữ giữa Mexico và Tây Ban Nha, ví dụ carro / coche, computadora / ordenador."] },
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
  ja: [
    { show: "逃げるは恥だが役に立つ", showId: "nigeru-wa-haji", status: "now", span: { zh: "第 1 年", vi: "Năm 1" },
      goal: { zh: "练习现代日常日语，积累 JLPT 词汇和句型。", vi: "Luyện tiếng Nhật đời thường và tích lũy từ vựng, mẫu câu JLPT." } },
    { show: "后续日剧待定", showVi: "Phim Nhật tiếp theo chưa chọn", status: "planned", span: { zh: "后续阶段", vi: "Giai đoạn sau" },
      goal: { zh: "用后续剧集扩展话题和语域。", vi: "Mở rộng chủ đề và ngữ vực qua các phim tiếp theo." } },
  ],
  fr: [
    { show: "Lupin", showId: "lupin", status: "now", span: { zh: "第 1 年", vi: "Năm 1" },
      goal: { zh: "以法国法语打底，按 CEFR 练习口语表达和叙事。", vi: "Xây nền tảng tiếng Pháp ở Pháp, luyện cách nói và kể chuyện theo CEFR." } },
    { show: "魁北克剧待定", showVi: "Phim Québec chưa chọn", status: "planned", span: { zh: "后续阶段", vi: "Giai đoạn sau" },
      goal: { zh: "学习魁北克法语的词汇、发音和口语差异。", vi: "Học khác biệt về từ vựng, phát âm và khẩu ngữ Québec." } },
  ],
  es: [
    { show: "La casa de las flores", showId: "la-casa-de-las-flores", status: "now", span: { zh: "第 1–2 年 · 核心课程", vi: "Năm 1–2 · chương trình chính" },
      goal: { zh: "用墨西哥城的家庭剧打底：日常口语、家庭称呼、ser / estar 和过去时，在语境里练到 B1。", vi: "Xây nền tảng bằng phim gia đình ở Thành phố Mexico: khẩu ngữ hằng ngày, xưng hô trong gia đình, ser / estar và thì quá khứ; luyện tới B1 trong ngữ cảnh." } },
    { show: "Club de Cuervos", showId: "club-de-cuervos", status: "now", span: { zh: "第 3 年 · 足球与生意模块", vi: "Năm 3 · học phần bóng đá và kinh doanh" },
      goal: { zh: "球队经营和家族生意：职场用语、谈判、墨西哥俚语和虚拟式，向 B2 推进。", vi: "Điều hành đội bóng và kinh doanh gia đình: từ ngữ công sở, đàm phán, tiếng lóng Mexico và thức giả định; tiến tới B2." } },
    { show: "西班牙本土西语剧待定", showVi: "Phim Tây Ban Nha chưa chọn", status: "planned", span: { zh: "后续阶段", vi: "Giai đoạn sau" },
      goal: { zh: "学习西班牙本土西语：vosotros、发音（区分 c / z 与 s）和用词差异。", vi: "Học tiếng Tây Ban Nha ở Tây Ban Nha: vosotros, phát âm (phân biệt c / z với s) và khác biệt từ vựng." } },
  ],
};
