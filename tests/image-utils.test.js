import { test } from "node:test";
import assert from "node:assert/strict";
import {
  computeScaledDimensions,
  clampQuality,
  compressionSavingsPercent,
  extensionForMime,
} from "../lib/image-utils.js";

test("computeScaledDimensions: يصغّر مع الحفاظ على النسبة", () => {
  // 2000x1000 ضمن حد 1000x1000 → 1000x500
  assert.deepEqual(computeScaledDimensions(2000, 1000, 1000, 1000), {
    width: 1000,
    height: 500,
  });
});

test("computeScaledDimensions: لا يكبّر الصور الصغيرة", () => {
  assert.deepEqual(computeScaledDimensions(400, 300, 1000, 1000), {
    width: 400,
    height: 300,
  });
});

test("computeScaledDimensions: أبعاد غير صالحة = صفر", () => {
  assert.deepEqual(computeScaledDimensions(0, 100, 500, 500), {
    width: 0,
    height: 0,
  });
});

test("clampQuality: يثبّت ضمن [0.1, 1]", () => {
  assert.equal(clampQuality(0.5), 0.5);
  assert.equal(clampQuality(5), 1);
  assert.equal(clampQuality(-1), 0.1);
  assert.equal(clampQuality(NaN), 0.8);
});

test("compressionSavingsPercent: حساب التوفير", () => {
  assert.equal(compressionSavingsPercent(1000, 600), 40);
  assert.equal(compressionSavingsPercent(1000, 1000), 0);
  assert.equal(compressionSavingsPercent(0, 500), 0);
});

test("extensionForMime: تعيين صحيح", () => {
  assert.equal(extensionForMime("image/jpeg"), "jpg");
  assert.equal(extensionForMime("image/png"), "png");
  assert.equal(extensionForMime("image/webp"), "webp");
  assert.equal(extensionForMime("image/unknown"), "img");
});
