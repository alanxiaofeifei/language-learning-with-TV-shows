import test from 'node:test';
import assert from 'node:assert/strict';
import { parseSubtitles } from '../site/import-subtitles.js';

test('SRT supports BOM, CRLF, multiline cues, markup and fractional seconds', () => {
  const input = '\uFEFF1\r\n00:00:02,250 --> 00:00:05,000\r\n<i>Xin chào!</i>\r\nEm chào anh.\r\n\r\n2\r\n00:00:06,000 --> 00:00:07,000\r\n[Music]';
  assert.deepEqual(parseSubtitles(input, 'tập 1.SRT'), [
    { text: 'Xin chào! Em chào anh.', startSeconds: 2.25 }
  ]);
});

test('WebVTT ignores metadata blocks and removes only overlapping duplicate cues', () => {
  const input = `WEBVTT
Language: vi

NOTE user comment
metadata

STYLE
::cue { color: white; }

first-cue
00:01.000 --> 00:03.500 align:start
<v Lan><c.green>Đúng <00:01.500>rồi.</c>

00:02.500 --> 00:04.000
Đúng rồi.

00:08.000 --> 00:09.000
Đúng rồi.`;
  assert.deepEqual(parseSubtitles(input), [
    { text: 'Đúng rồi.', startSeconds: 1 },
    { text: 'Đúng rồi.', startSeconds: 8 }
  ]);
});

test('YouTube transcripts accept inline and separate timecodes, wrapped lines and hours', () => {
  const input = '0:00\nXin chào\ncác bạn!\n0:08 Cảm ơn.\n[1:02:03] Tạm biệt!';
  assert.deepEqual(parseSubtitles(input, 'pasted.txt'), [
    { text: 'Xin chào các bạn!', startSeconds: 0 },
    { text: 'Cảm ơn.', startSeconds: 8 },
    { text: 'Tạm biệt!', startSeconds: 3723 }
  ]);
});

test('unmarked pasted dialogue keeps separate lines and literal decoded text', () => {
  assert.deepEqual(parseSubtitles('A &amp; B\rTôi đọc [chữ này].\n\n&lt;i&gt; &#x111;'), [
    { text: 'A & B', startSeconds: null },
    { text: 'Tôi đọc [chữ này].', startSeconds: null },
    { text: '<i> đ', startSeconds: null }
  ]);
});

test('invalid uploads and malformed timing produce actionable errors', () => {
  assert.throws(() => parseSubtitles(' '), /粘贴台词/);
  assert.throws(() => parseSubtitles('WEBVTT\n\nNOTE only notes'), /没有可学习/);
  assert.throws(() => parseSubtitles('hello', 'video.mp4'), /SRT、VTT 或 TXT/);
  assert.throws(() => parseSubtitles('not timed', 'broken.srt'), /时间码无效/);
  assert.throws(() => parseSubtitles('00:00:62 --> 00:00:05\nHello'), /时间码无效/);
  assert.throws(() => parseSubtitles('00:10.000 --> 00:02.000\nHello'), /时间码无效/);
});
