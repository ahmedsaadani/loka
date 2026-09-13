import { describe, expect, it } from "vitest";

import { addMonths, cn, formatEur, formatPrice, formatTnd, pluralize, toIsoDate } from "./utils";

describe("utils", () => {
  it("cn merges tailwind classes", () => {
    expect(cn("p-2", "p-4", false && "hidden")).toBe("p-4");
  });

  it("formats TND without decimals", () => {
    expect(formatTnd("850.00")).toMatch(/850\s?DT$/);
    expect(formatTnd(1250)).toMatch(/^1\s?250\s?DT$/);
  });

  it("formats EUR", () => {
    expect(formatEur("250.75")).toContain("€");
  });

  it("formats price with unit", () => {
    expect(formatPrice("120", "nightly")).toMatch(/120 DT \/ nuit/);
    expect(formatPrice("850", "monthly")).toMatch(/850 DT \/ mois/);
  });

  it("iso date and month arithmetic", () => {
    const start = new Date(2026, 0, 31);
    expect(toIsoDate(start)).toBe("2026-01-31");
    expect(toIsoDate(addMonths(new Date(2026, 0, 10), 1))).toBe("2026-02-10");
  });

  it("pluralize", () => {
    expect(pluralize(1, "nuit")).toBe("1 nuit");
    expect(pluralize(3, "nuit")).toBe("3 nuits");
    expect(pluralize(2, "mois", "mois")).toBe("2 mois");
  });
});
