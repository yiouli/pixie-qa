import { describe, it, expect } from "vitest";

import { XSadd } from "..";

const resultUint32 = [
  1823491521, 1658333335, 1467485721, 45623648, 3336175492, 2561136018,
  181953608, 768231638, 3747468990, 633754442, 1317015417, 2329323117,
  688642499, 1053686614, 1029905208, 3711673957, 2701869769, 695757698,
  3819984643, 1221024953,
];

const resultFloat = [
  0.03331006, 0.81703216, 0.52816284, 0.76104426, 0.09285593, 0.34277064,
  0.40109116, 0.79619718, 0.71619844, 0.21930778, 0.68432468, 0.05859083,
  0.86583626, 0.22139138, 0.95107985, 0.15838248, 0.02087647, 0.60301602,
  0.01047146, 0.34406352,
];

describe("check return values", () => {
  const xsadd = new XSadd(1234);

  it("uint32", () => {
    const result: number[] = [];
    for (let i = 0; i < 40; i++) {
      const value = xsadd.getUint32();
      if (i < 20) {
        result.push(value);
      }
    }
    expect(result).toEqual(resultUint32);
  });

  it("float", () => {
    const result: number[] = [];
    for (let i = 0; i < 20; i++) {
      result.push(xsadd.getFloat());
    }
    for (const [i, value] of result.entries()) {
      expect(value).toBeCloseTo(resultFloat[i], 1e-6);
    }
  });
});

it("should be reinintiable", () => {
  const xsadd = new XSadd(1234);
  const val1 = xsadd.getUint32();
  const val2 = xsadd.getFloat();

  xsadd.init(1234);
  expect(xsadd.getUint32()).toBe(val1);
  expect(xsadd.getFloat()).toBe(val2);

  xsadd.init(42);
  expect(xsadd.getUint32()).not.toBe(val1);
  expect(xsadd.getFloat()).not.toBe(val2);
});

it("should export a standalone random()", () => {
  const xsadd = new XSadd(1234);
  const value = xsadd.random();
  expect(typeof value).toBe("number");
  const random = xsadd.random;
  random();
  random();
  expect(typeof random()).toBe("number");
});

it("should throw if seed is not an integer", () => {
  const add = new XSadd();
  // eslint-disable-next-line unicorn/no-array-for-each
  [false, Infinity, Number.NaN, "1", 0.2, 4.5].forEach((value: any) => {
    expect(() => new XSadd(value)).toThrow(/seed must be an integer/);
    expect(() => add.init(value)).toThrow(/seed must be an integer/);
  });
});
