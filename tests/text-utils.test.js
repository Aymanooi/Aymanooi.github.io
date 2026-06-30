import { test } from "node:test";
import assert from "node:assert/strict";
import {
  countWords,
  countCharacters,
  countSentences,
  countParagraphs,
  readingTimeMinutes,
  formatBytes,
} from "../lib/text-utils.js";

test("countWords: نص فارغ أو غير صالح = 0", () => {
  assert.equal(countWords(""), 0);
  assert.equal(countWords("   "), 0);
  assert.equal(countWords(null), 0);
  assert.equal(countWords(undefined), 0);
});

test("countWords: عربي وإنجليزي مع مسافات متعددة", () => {
  assert.equal(countWords("مرحبا بالعالم"), 2);
  assert.equal(countWords("  hello   world  "), 2);
  assert.equal(countWords("كلمة\nسطر\tجديد"), 3);
});

test("countCharacters: مع وبدون مسافات", () => {
  assert.equal(countCharacters("abc"), 3);
  assert.equal(countCharacters("a b c"), 5);
  assert.equal(countCharacters("a b c", { includeSpaces: false }), 3);
});

test("countCharacters: الإيموجي يُحسب كحرف واحد", () => {
  assert.equal(countCharacters("👍"), 1);
  assert.equal(countCharacters("ab👍"), 3);
});

test("countSentences: علامات عربية ولاتينية", () => {
  assert.equal(countSentences("جملة أولى. جملة ثانية!"), 2);
  assert.equal(countSentences("هل أنت بخير؟ نعم."), 2);
  assert.equal(countSentences(""), 0);
  assert.equal(countSentences("بدون علامة"), 1);
});

test("countParagraphs: مفصولة بأسطر فارغة", () => {
  assert.equal(countParagraphs("فقرة واحدة"), 1);
  assert.equal(countParagraphs("فقرة 1\n\nفقرة 2"), 2);
  assert.equal(countParagraphs("\n\n\n"), 0);
});

test("readingTimeMinutes: حد أدنى دقيقة لنص غير فارغ", () => {
  assert.equal(readingTimeMinutes(""), 0);
  assert.equal(readingTimeMinutes("كلمة واحدة فقط"), 1);
  const longText = Array(400).fill("كلمة").join(" ");
  assert.equal(readingTimeMinutes(longText, 200), 2);
});

test("formatBytes: تحويل صحيح للوحدات", () => {
  assert.equal(formatBytes(0), "0 B");
  assert.equal(formatBytes(512), "512 B");
  assert.equal(formatBytes(1024), "1 KB");
  assert.equal(formatBytes(1536), "1.5 KB");
  assert.equal(formatBytes(1048576), "1 MB");
  assert.equal(formatBytes(-5), "—");
});
