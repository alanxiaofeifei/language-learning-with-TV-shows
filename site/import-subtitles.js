// Return plain text. Render each cue using textContent, including decoded entities.
function cueText(lines) {
  const entities = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', lrm: '', rlm: '' };
  return lines.join(' ')
    .replace(/<br\s*\/?>/gi, ' ')
    .replace(/<\/?[a-z][^<>]*>|<\d[\d:.,]*>/gi, '')
    .replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos|nbsp|lrm|rlm);/gi, (_, entity) => {
      const key = entity.toLowerCase();
      if (key in entities) return entities[key];
      const point = key.startsWith('#x') ? Number.parseInt(key.slice(2), 16) : Number(key.slice(1));
      return point > 0 && point <= 0x10ffff && !(point >= 0xd800 && point <= 0xdfff)
        ? String.fromCodePoint(point) : '\ufffd';
    })
    .replace(/\[\s*(?:music|applause|laughter|laughs?|sighs?|cheering|âm nhạc|nhạc(?: nền)?|tiếng (?:cười|vỗ tay)|音乐|掌声|笑声)\s*\]/gi, ' ')
    .replace(/[♪♫]/g, ' ')
    .replace(/^\s*>>\s*/, '')
    .replace(/\s+/g, ' ')
    .trim();
}

const clockPattern = /^(?:(\d+):)?(\d+):([0-5]\d)(?:[.,](\d{1,3}))?$/;

function seconds(value) {
  const parts = clockPattern.exec(value);
  if (!parts) return null;
  const [, hours, minutes, wholeSeconds, fraction = ''] = parts;
  if (hours !== undefined && Number(minutes) >= 60) return null;
  const total = Number(hours ?? 0) * 3600 + Number(minutes) * 60 + Number(wholeSeconds);
  return Number.isSafeInteger(total) ? total + Number(`0.${fraction}`) : null;
}

function parseTimed(source) {
  const cues = [];
  let previousEnd = null;
  for (const block of source.split(/\n[\t ]*\n/)) {
    const lines = block.trim().split('\n');
    if (!lines[0] || /^(?:WEBVTT|NOTE|STYLE|REGION)(?:\s|$)/.test(lines[0])) continue;
    const timing = lines[0].includes('-->') ? 0 : 1; // Optional cue ID precedes the timing line.
    const times = /^\s*(\S+)\s*-->\s*(\S+)(?:\s+.*)?$/.exec(lines[timing] ?? '');
    const start = times && seconds(times[1]);
    const end = times && seconds(times[2]);
    if (start === null || end === null || end <= start) {
      throw new Error(`字幕时间码无效，请检查「${(lines[timing] ?? lines[0]).slice(0, 75)}」。`);
    }
    const text = cueText(lines.slice(timing + 1));
    if (!text) continue;
    // Rolling captions can emit the same words again in an overlapping cue.
    if (text === cues.at(-1)?.text && start >= cues.at(-1).startSeconds && start < previousEnd) {
      previousEnd = Math.max(previousEnd, end);
      continue;
    }
    cues.push({ text, startSeconds: start });
    previousEnd = end;
  }
  return cues;
}

function parseTranscript(source) {
  const cues = [];
  const stamp = /^(?:\[(\d+(?::\d{2}){1,2}(?:[.,]\d{1,3})?)\]\s*|(\d+(?::\d{2}){1,2}(?:[.,]\d{1,3})?)(?:\s+|$))(.*)$/;
  let timestamp = null;
  let words = [];
  function emit() {
    const text = cueText(words);
    if (text) cues.push({ text, startSeconds: timestamp });
    words = [];
  }
  for (const raw of source.split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    const match = stamp.exec(line);
    if (match) {
      emit();
      timestamp = seconds(match[1] ?? match[2]);
      if (timestamp === null) throw new Error('台词中的时间标记无效。');
      words.push(match[3]);
    } else {
      words.push(line);
      if (timestamp === null) emit();
    }
  }
  emit();
  return cues;
}

export function parseSubtitles(source, filename = '') {
  if (typeof source !== 'string' || !source.trim()) {
    throw new Error('请选择字幕文件或粘贴台词。');
  }
  const input = source.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim();
  const extension = filename.split('.').at(-1).toLowerCase();
  if (filename && !['srt', 'vtt', 'txt'].includes(extension)) {
    throw new Error('请选择 SRT、VTT 或 TXT 文件。');
  }
  const timed = ['srt', 'vtt'].includes(extension) || /^WEBVTT\b/.test(input) || /^\s*\d[\d:.,]*\s*-->/m.test(input);
  const cues = timed ? parseTimed(input) : parseTranscript(input);
  if (!cues.length) throw new Error('内容中没有可学习的台词，请检查字幕或粘贴文本。');
  return cues;
}
