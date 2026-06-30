// دوال نقية لحسابات الصور — منفصلة عن Canvas DOM لتكون قابلة للاختبار.

/**
 * حساب أبعاد جديدة مع المحافظة على نسبة العرض/الارتفاع ضمن حد أقصى.
 * إذا كانت الصورة أصغر من الحد، تُترك كما هي (لا تكبير).
 * @param {number} width
 * @param {number} height
 * @param {number} maxWidth
 * @param {number} maxHeight
 * @returns {{ width: number, height: number }}
 */
export function computeScaledDimensions(width, height, maxWidth, maxHeight) {
  if (width <= 0 || height <= 0) return { width: 0, height: 0 };
  const wRatio = maxWidth > 0 ? maxWidth / width : 1;
  const hRatio = maxHeight > 0 ? maxHeight / height : 1;
  // لا نكبّر الصورة: أقصى نسبة = 1
  const ratio = Math.min(wRatio, hRatio, 1);
  return {
    width: Math.max(1, Math.round(width * ratio)),
    height: Math.max(1, Math.round(height * ratio)),
  };
}

/**
 * تثبيت قيمة الجودة ضمن المجال [0.1, 1].
 * @param {number} quality
 * @returns {number}
 */
export function clampQuality(quality) {
  if (!Number.isFinite(quality)) return 0.8;
  return Math.min(1, Math.max(0.1, quality));
}

/**
 * حساب نسبة التوفير في الحجم كنسبة مئوية (موجبة = توفير).
 * @param {number} originalBytes
 * @param {number} newBytes
 * @returns {number} نسبة مئوية مقرّبة لرقم عشري واحد
 */
export function compressionSavingsPercent(originalBytes, newBytes) {
  if (!Number.isFinite(originalBytes) || originalBytes <= 0) return 0;
  if (!Number.isFinite(newBytes) || newBytes < 0) return 0;
  const savings = ((originalBytes - newBytes) / originalBytes) * 100;
  return Math.round(savings * 10) / 10;
}

/**
 * تحديد امتداد الملف الناتج من نوع MIME.
 * @param {string} mimeType
 * @returns {string}
 */
export function extensionForMime(mimeType) {
  const map = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
  };
  return map[mimeType] || "img";
}
