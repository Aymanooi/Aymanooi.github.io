import { test } from "node:test";
import assert from "node:assert/strict";
import {
  formatJson,
  minifyJson,
  isValidJson,
} from "../lib/json-utils.js";

test("formatJson: ينسّق كائنًا صحيحًا", () => {
  const r = formatJson('{"a":1,"b":[2,3]}', 2);
  assert.equal(r.ok, true);
  assert.equal(r.result, '{\n  "a": 1,\n  "b": [\n    2,\n    3\n  ]\n}');
});

test("formatJson: يفشل بلطف على إدخال غير صالح", () => {
  const r = formatJson("{بلا اقتباس}");
  assert.equal(r.ok, false);
  assert.match(r.error, /JSON/);
});

test("formatJson: النص الفارغ يفشل برسالة واضحة", () => {
  const r = formatJson("   ");
  assert.equal(r.ok, false);
  assert.equal(r.error, "النص فارغ");
});

test("minifyJson: يزيل المسافات", () => {
  const r = minifyJson('{\n  "a": 1\n}');
  assert.equal(r.ok, true);
  assert.equal(r.result, '{"a":1}');
});

test("isValidJson: تمييز الصالح من غير الصالح", () => {
  assert.equal(isValidJson('{"x":1}'), true);
  assert.equal(isValidJson("[1,2,3]"), true);
  assert.equal(isValidJson('{"x":}'), false);
  assert.equal(isValidJson(""), false);
  assert.equal(isValidJson(null), false);
});
