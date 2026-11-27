// 12-week plan: week 1 = pronunciation + P01, then P02..P82 spread over days 8..84.
export const TOTAL_PARTS = 82;
export const WEEKS = [
  { week: 1, title: "发音与声调", focus: "6 个声调、北音辅音（d/gi/r 读 z）、元音、词尾；称呼体系", topic: "social" },
  { week: 2, title: "生存句", focus: "打招呼、谢谢、对不起、多少钱、要这个", topic: "survival" },
  { week: 3, title: "吃饭点菜", focus: "点菜、好吃、买单、不要辣", topic: "food" },
  { week: 4, title: "买东西讲价", focus: "多少钱、便宜点、要/不要", topic: "shopping" },
  { week: 5, title: "问路与出行", focus: "在哪里、怎么走、打车、几点", topic: "survival" },
  { week: 6, title: "日常寒暄", focus: "问候、关心、客气话", topic: "social" },
  { week: 7, title: "职场寒暄", focus: "同事、上级、请假、加班", topic: "work" },
  { week: 8, title: "听懂指令", focus: "做什么、快点、小心；第二遍关字幕", topic: "work" },
  { week: 9, title: "情绪与劝说", focus: "安慰、劝说、拒绝", topic: "feeling" },
  { week: 10, title: "电话与约定", focus: "约时间、电话用语", topic: "social" },
  { week: 11, title: "综合听力", focus: "越语字幕或无字幕看", topic: "feeling" },
  { week: 12, title: "总复习", focus: "复习卡清零、自测", topic: "work" },
];

export const PRON_LESSONS = ["tones", "consonants", "vowels", "finals", "address"];

export function buildDays(totalParts = TOTAL_PARTS) {
  const days = [];
  PRON_LESSONS.forEach((lesson, i) => days.push({ day: i + 1, week: 1, pron: lesson, parts: i === 4 ? [] : [] }));
  days.push({ day: 6, week: 1, pron: null, parts: [1] });
  days.push({ day: 7, week: 1, pron: null, parts: [], reviewOnly: true });
  const rest = totalParts - 1, slots = 77;
  for (let d = 0; d < slots; d++) {
    const from = 2 + Math.floor((d * rest) / slots), to = 2 + Math.floor(((d + 1) * rest) / slots);
    const parts = []; for (let p = from; p < to; p++) parts.push(p);
    days.push({ day: 8 + d, week: 2 + Math.floor(d / 7), pron: null, parts });
  }
  return days;
}

export function nextDay(days, doneDays) {
  return days.find((d) => !doneDays.includes(d.day)) || days[days.length - 1];
}
