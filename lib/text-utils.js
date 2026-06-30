// دوال نقية لتحليل النص — قابلة للاستخدام في المتصفح وفي اختبارات Node.
// كل دالة هنا خالية من الأثر الجانبي (pure) لتسهيل الاختبار.

/**
 * عدّ الكلمات. يتعامل مع المسافات المتعددة والأسطر والعربية والإنجليزية.
 * @param {string} text
 * @returns {number}
 */
export function countWords(text) {
  if (!text || typeof text !== "string") return 0;
  const matches = text.trim().match(/\S+/g);
  return matches ? matches.length : 0;
}

/**
 * عدّ الأحرف.
 * @param {string} text
 * @param {{ includeSpaces?: boolean }} [opts]
 * @returns {number}
 */
export function countCharacters(text, opts = {}) {
  if (!text || typeof text !== "string") return 0;
  const includeSpaces = opts.includeSpaces !== false; // الافتراضي: يشمل المسافات
  // نستخدم spread لاحتساب الرموز فوق BMP (مثل الإيموجي) كحرف واحد.
  const chars = [...text];
  if (includeSpaces) return chars.length;
  return chars.filter((c) => !/\s/.test(c)).length;
}

/**
 * عدّ الجُمل (تقريبي) بالاعتماد على علامات الترقيم النهائية العربية واللاتينية.
 * @param {string} text
 * @returns {number}
 */
export function countSentences(text) {
  if (!text || typeof text !== "string") return 0;
  const trimmed = text.trim();
  if (!trimmed) return 0;
  // فواصل الجُمل: . ! ? وعلامة الاستفهام العربية ؟
  const parts = trimmed.split(/[.!?؟]+/).filter((s) => s.trim().length > 0);
  return parts.length;
}

/**
 * عدّ الفقرات (كتل مفصولة بسطر فارغ أو أكثر).
 * @param {string} text
 * @returns {number}
 */
export function countParagraphs(text) {
  if (!text || typeof text !== "string") return 0;
  const parts = text.split(/\n\s*\n/).filter((p) => p.trim().length > 0);
  return parts.length;
}

/**
 * تقدير زمن القراءة بالدقائق (الافتراضي 200 كلمة/دقيقة).
 * @param {string} text
 * @param {number} [wpm=200]
 * @returns {number} عدد الدقائق (مقرّب لأعلى، بحد أدنى 0 لنص فارغ)
 */
export function readingTimeMinutes(text, wpm = 200) {
  const words = countWords(text);
  if (words === 0) return 0;
  return Math.max(1, Math.ceil(words / wpm));
}

/**
 * تنسيق حجم بالبايت إلى وحدة مقروءة (B, KB, MB, GB).
 * @param {number} bytes
 * @param {number} [decimals=1]
 * @returns {string}
 */
export function formatBytes(bytes, decimals = 1) {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes === 0) return "0 B";
  const k = 1024;
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), units.length - 1);
  const value = bytes / Math.pow(k, i);
  return `${parseFloat(value.toFixed(decimals))} ${units[i]}`;
}
