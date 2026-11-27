// Long track (~5 years, 260 weeks) on the same 82 VFC parts.
// First pass (stages 1–5) covers every part exactly once; later weeks are review, rewatch, or cycles.

export const LONG_TOTAL_WEEKS = 260;

export const WORK_TOPICS = [
  { id: "leave", title: "请假与安排", vi: "Tôi muốn xin nghỉ phép ngày mai.", zh: "我想请明天的假。", reading: "toi↗ muon↘ xin nghi↘ phep↘ ngay mai", note: "跟主管说日期和时长。自编补充例句，不是剧中台词。" },
  { id: "overtime", title: "加班", vi: "Hôm nay có tăng ca không?", zh: "今天要加班吗？", reading: "hom nay co↗ tang ca khong", note: "先问清楚再答应。自编补充例句，不是剧中台词。" },
  { id: "shift", title: "班次", vi: "Ca đêm bắt đầu lúc mấy giờ?", zh: "夜班几点开始？", reading: "ca dem↗ bat dau luc may gio↘", note: "问清交接时间。自编补充例句，不是剧中台词。" },
  { id: "defect", title: "品质不良", vi: "Lô hàng này bị lỗi, cần kiểm tra lại.", zh: "这批货有不良，需要再检查。", reading: "lo hang nay bi↘ loi↘, can kiem tra lai", note: "说清楚批次和现象。自编补充例句，不是剧中台词。" },
  { id: "outage", title: "系统故障", vi: "Hệ thống bị sự cố, tôi đang kiểm tra.", zh: "系统出故障了，我正在检查。", reading: "he thong bi↘ su co, toi dang kiem tra", note: "先报现状，再给预计。自编补充例句，不是剧中台词。" },
  { id: "ticket", title: "工单", vi: "Anh gửi ticket giúp em với.", zh: "请帮我提一个工单。", reading: "anh↘ gui ticket giup em voi", note: "称呼按对方年龄/职位改 anh/chị。自编补充例句，不是剧中台词。" },
  { id: "network", title: "网络与电脑", vi: "Máy tính không vào được mạng.", zh: "这台电脑上不了网。", reading: "may tinh khong vao duoc mang", note: "自编补充例句，不是剧中台词。" },
  { id: "report", title: "汇报", vi: "Em báo cáo tình hình ca này ạ.", zh: "我汇报一下这一班的情况。", reading: "em bao cao tinh hinh ca nay ạ", note: "开头先称呼 + ạ。自编补充例句，不是剧中台词。" },
  { id: "handover", title: "交接", vi: "Ca này đã bàn giao xong chưa?", zh: "这一班交接完了吗？", reading: "ca nay da↗ ban giao xong chua", note: "自编补充例句，不是剧中台词。" },
  { id: "deadline", title: "期限", vi: "Deadline là ngày mai, mình cố gắng nhé.", zh: "截止日期是明天，我们加把劲。", reading: "deadline la ngay mai, minh co gan nhe", note: "自编补充例句，不是剧中台词。" },
];

export const LONG_STAGES = [
  {
    id: "footing",
    title: "立足",
    yearHint: "第 1 年前期",
    months: 6,
    weekStart: 1,
    weekCount: 26,
    partStart: 1,
    partEnd: 16,
    goal: "声调稳定，能打招呼、问路、点餐、买东西，谢谢和对不起能脱口而出。和短期版内容重叠，但每周只精读一段，练到能用。",
    grammar: "人称与称呼（tôi / mình / anh / chị / em）、là 与 không / chưa、疑问词（gì, đâu, bao nhiêu）、常用量词 cái / con。",
    skills: ["发音与 6 声", "生存句", "点餐购物", "跟读原声"],
  },
  {
    id: "daily",
    title: "日常自如",
    yearHint: "第 1 年后期",
    months: 6,
    weekStart: 27,
    weekCount: 26,
    partStart: 17,
    partEnd: 32,
    goal: "生活场景能听懂大意，能把要做的事说清楚，不再只靠几个关键词。",
    grammar: "已然 / 进行 / 完成（đã, đang, rồi）、muốn / cần / phải、时间与方位、简单比较。",
    skills: ["听大意", "把事情说完整", "少看中文字幕"],
  },
  {
    id: "social",
    title: "社交与分寸",
    yearHint: "第 2 年",
    months: 12,
    weekStart: 53,
    weekCount: 52,
    partStart: 33,
    partEnd: 50,
    goal: "听出语气和关系，会客气、会拒绝、会安慰，称呼不再用错。",
    grammar: "语气词 ạ / nhé / à / đi / thôi、关系从句 mà、连动结构、委婉拒绝。",
    skills: ["称呼体系", "情绪与劝说", "礼貌程度"],
  },
  {
    id: "work",
    title: "职场沟通",
    yearHint: "第 3 年",
    months: 12,
    weekStart: 105,
    weekCount: 52,
    partStart: 51,
    partEnd: 68,
    goal: "在 Chilisin 工厂 IT 环境能听懂指令、请假加班、汇报故障、讨论品质问题。剧中用语继续精读，并配自编职场补充包。",
    grammar: "được / bị、因果（vì… nên）、转述、较正式口吻、数字与规格。",
    skills: ["听指令", "请假与加班", "故障与品质", "简短汇报"],
    workPack: true,
  },
  {
    id: "native",
    title: "接近母语听力",
    yearHint: "第 4 年",
    months: 12,
    weekStart: 157,
    weekCount: 52,
    partStart: 69,
    partEnd: 82,
    goal: "少看或关掉中文字幕，听出言外之意和北越口语里的省略。前半部回看，把语速提上去。",
    grammar: "省略、反问与讽刺、北方口语虚词、语速与连读。",
    skills: ["无中文字幕", "听言外之意", "回看前半部"],
    rewatchBefore: 68,
  },
  {
    id: "maintain",
    title: "循环保持",
    yearHint: "第 5 年",
    months: 12,
    weekStart: 209,
    weekCount: 52,
    partStart: 1,
    partEnd: 82,
    goal: "不回生。每周重听、跟读，偶尔听写；复习卡只维持仍然会忘的句子。",
    grammar: "语域切换（家里 / 同事 / 上级）、自我听写纠错。",
    skills: ["跟读", "听写", "维持复习"],
    cycle: true,
  },
];

export const WEEK_MODES = {
  deep: "精读：先学用语，再配双语字幕看这一段，然后跟读原声。",
  review: "复习周：重听本阶段最近几段的难句，把到期卡片做完。",
  rewatch: "回看：尽量少看中文字幕，只在卡壳时打开。",
  cycle: "循环：重听并跟读，挑 5 句听写。",
};

function range(from, to) {
  const out = [];
  for (let n = from; n <= to; n++) out.push(n);
  return out;
}

function placeReviews(weekCount, reviewCount) {
  const slots = Array(weekCount).fill("study");
  if (reviewCount <= 0) return slots;
  const used = new Set();
  for (let i = 1; i <= reviewCount; i++) {
    let pos = Math.round((i * weekCount) / (reviewCount + 1));
    if (pos <= 0) pos = 1;
    if (pos >= weekCount) pos = weekCount - 1;
    while (used.has(pos) || pos === 0) {
      pos += 1;
      if (pos >= weekCount) pos = 1;
    }
    used.add(pos);
    slots[pos] = "review";
  }
  return slots;
}

function chunkParts(parts, weekCount) {
  const chunks = [];
  for (let i = 0; i < weekCount; i++) {
    const from = Math.floor((i * parts.length) / weekCount);
    const to = Math.floor(((i + 1) * parts.length) / weekCount);
    chunks.push(parts.slice(from, to));
  }
  return chunks;
}

export function buildLongWeeks(totalParts = 82) {
  const weeks = [];
  for (const stage of LONG_STAGES) {
    const firstPassParts = range(stage.partStart, Math.min(stage.partEnd, totalParts));
    if (stage.cycle) {
      const chunks = chunkParts(range(1, totalParts), stage.weekCount);
      chunks.forEach((parts, i) => {
        weeks.push({
          week: stage.weekStart + i,
          stage: stage.id,
          mode: "cycle",
          parts,
          topic: null,
        });
      });
      continue;
    }
    if (stage.rewatchBefore) {
      const deepSlots = firstPassParts.length;
      const rewatchCount = stage.weekCount - deepSlots;
      const earlier = range(1, Math.min(stage.rewatchBefore, totalParts));
      const rewatchChunks = chunkParts(earlier, rewatchCount);
      let r = 0;
      for (let i = 0; i < stage.weekCount; i++) {
        if (i < deepSlots) {
          weeks.push({
            week: stage.weekStart + i,
            stage: stage.id,
            mode: "deep",
            parts: [firstPassParts[i]],
            topic: null,
          });
        } else {
          weeks.push({
            week: stage.weekStart + i,
            stage: stage.id,
            mode: "rewatch",
            parts: rewatchChunks[r++] || [],
            topic: null,
          });
        }
      }
      continue;
    }
    const reviewCount = stage.weekCount - firstPassParts.length;
    const slots = placeReviews(stage.weekCount, reviewCount);
    let p = 0;
    const seen = [];
    let topicIdx = 0;
    slots.forEach((kind, i) => {
      if (kind === "study") {
        const part = firstPassParts[p++];
        seen.push(part);
        weeks.push({
          week: stage.weekStart + i,
          stage: stage.id,
          mode: "deep",
          parts: [part],
          topic: stage.workPack ? WORK_TOPICS[topicIdx++ % WORK_TOPICS.length] : null,
        });
      } else {
        weeks.push({
          week: stage.weekStart + i,
          stage: stage.id,
          mode: "review",
          parts: seen.slice(-3),
          topic: stage.workPack ? WORK_TOPICS[topicIdx++ % WORK_TOPICS.length] : null,
        });
      }
    });
  }
  return weeks;
}

export function stageById(id) {
  return LONG_STAGES.find((s) => s.id === id) || null;
}

export function nextWeek(weeks, doneWeeks) {
  return weeks.find((w) => !doneWeeks.includes(w.week)) || weeks[weeks.length - 1];
}

export function firstPassParts(weeks) {
  return weeks.filter((w) => w.mode === "deep").flatMap((w) => w.parts);
}
