import { beforeEach, describe, expect, it, vi } from "vitest";

const { hospitalSingleMock, yearsLimitMock } = vi.hoisted(() => ({
  hospitalSingleMock: vi.fn(),
  yearsLimitMock: vi.fn(),
}));

vi.mock("./supabaseClient", () => {
  const hospitalsBuilder = {
    select: vi.fn(() => hospitalsBuilder),
    eq: vi.fn(() => hospitalsBuilder),
    maybeSingle: hospitalSingleMock,
  };
  const yearsBuilder = {
    select: vi.fn(() => yearsBuilder),
    eq: vi.fn(() => yearsBuilder),
    order: vi.fn(() => yearsBuilder),
    limit: yearsLimitMock,
  };
  return {
    supabase: {
      from: vi.fn((table: string) =>
        table === "hospitals" ? hospitalsBuilder : yearsBuilder
      ),
    },
  };
});

import { formatMetric, getHospitalTrends } from "./hospitalDetail";

const REAL_HOSPITAL = {
  provider_ccn: "670781",
  name: "ANSON GENERAL HOSPITAL",
  state: "TX",
};

describe("getHospitalTrends", () => {
  beforeEach(() => {
    hospitalSingleMock.mockReset();
    yearsLimitMock.mockReset();
  });

  it("returns three years of trends in ascending fiscal-year order (happy path)", async () => {
    hospitalSingleMock.mockResolvedValueOnce({
      data: REAL_HOSPITAL,
      error: null,
    });
    // DB query orders descending + limit 3; mock reflects that shape.
    yearsLimitMock.mockResolvedValueOnce({
      data: [
        { fiscal_year: 2025, operating_margin_pct: -1.2, days_cash_on_hand: 10, days_in_ar: 40 },
        { fiscal_year: 2024, operating_margin_pct: 0.5, days_cash_on_hand: 12, days_in_ar: 38 },
        { fiscal_year: 2023, operating_margin_pct: 1.1, days_cash_on_hand: 14, days_in_ar: 35 },
      ],
      error: null,
    });

    const result = await getHospitalTrends("670781");

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.hospital.years.map((y) => y.fiscal_year)).toEqual([
        2023, 2024, 2025,
      ]);
    }
  });

  it("returns fewer than three years without fabricating the gap", async () => {
    hospitalSingleMock.mockResolvedValueOnce({
      data: REAL_HOSPITAL,
      error: null,
    });
    yearsLimitMock.mockResolvedValueOnce({
      data: [
        { fiscal_year: 2024, operating_margin_pct: 0.5, days_cash_on_hand: 12, days_in_ar: 38 },
      ],
      error: null,
    });

    const result = await getHospitalTrends("670781");

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.hospital.years).toHaveLength(1);
    }
  });

  it("reports not_found when the hospital does not exist (not-found path)", async () => {
    hospitalSingleMock.mockResolvedValueOnce({ data: null, error: null });

    const result = await getHospitalTrends("000000");

    expect(result).toEqual({ ok: false, kind: "not_found" });
    expect(yearsLimitMock).not.toHaveBeenCalled();
  });

  it("surfaces a data-retrieval error from the hospital lookup", async () => {
    hospitalSingleMock.mockResolvedValueOnce({
      data: null,
      error: { message: "connection timeout" },
    });

    const result = await getHospitalTrends("670781");

    expect(result).toEqual({
      ok: false,
      kind: "error",
      error: "connection timeout",
    });
  });

  it("surfaces a data-retrieval error from the trend-years lookup", async () => {
    hospitalSingleMock.mockResolvedValueOnce({
      data: REAL_HOSPITAL,
      error: null,
    });
    yearsLimitMock.mockResolvedValueOnce({
      data: null,
      error: { message: "connection timeout" },
    });

    const result = await getHospitalTrends("670781");

    expect(result).toEqual({
      ok: false,
      kind: "error",
      error: "connection timeout",
    });
  });
});

describe("formatMetric", () => {
  it("formats a numeric value with its unit", () => {
    expect(formatMetric(1.5, "%")).toBe("1.5%");
  });

  it("never renders a missing metric as zero or blank", () => {
    expect(formatMetric(null, "%")).toBe("not available");
  });
});
