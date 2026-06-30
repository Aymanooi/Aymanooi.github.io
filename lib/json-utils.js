// دوال نقية لمعالجة JSON — تنسيق، تصغير، تحقّق.

/**
 * تنسيق نص JSON بمسافة بادئة محددة.
 * @param {string} input
 * @param {number} [indent=2]
 * @returns {{ ok: true, result: string } | { ok: false, error: string }}
 */
export function formatJson(input, indent = 2) {
  if (typeof input !== "string" || input.trim() === "") {
    return { ok: false, error: "النص فارغ" };
  }
  try {
    const parsed = JSON.parse(input);
    return { ok: true, result: JSON.stringify(parsed, null, indent) };
  } catch (e) {
    return { ok: false, error: humanizeJsonError(e) };
  }
}

/**
 * تصغير نص JSON (إزالة المسافات).
 * @param {string} input
 * @returns {{ ok: true, result: string } | { ok: false, error: string }}
 */
export function minifyJson(input) {
  if (typeof input !== "string" || input.trim() === "") {
    return { ok: false, error: "النص فارغ" };
  }
  try {
    const parsed = JSON.parse(input);
    return { ok: true, result: JSON.stringify(parsed) };
  } catch (e) {
    return { ok: false, error: humanizeJsonError(e) };
  }
}

/**
 * التحقق من صلاحية JSON.
 * @param {string} input
 * @returns {boolean}
 */
export function isValidJson(input) {
  if (typeof input !== "string" || input.trim() === "") return false;
  try {
    JSON.parse(input);
    return true;
  } catch {
    return false;
  }
}

/**
 * تحويل رسالة الخطأ إلى صيغة أوضح للمستخدم العربي.
 * @param {unknown} e
 * @returns {string}
 */
export function humanizeJsonError(e) {
  const msg = e && e.message ? String(e.message) : "صيغة JSON غير صحيحة";
  // محاولة استخراج رقم الموضع إن وُجد
  const posMatch = msg.match(/position (\d+)/i);
  if (posMatch) {
    return `صيغة JSON غير صحيحة عند الموضع ${posMatch[1]}`;
  }
  return `صيغة JSON غير صحيحة: ${msg}`;
}
