import { describe, expect, it, vi } from "vitest";

// Mock the Supabase client before importing the module under test, so no
// real network call happens in unit tests. Each test configures the
// resolved value of the chained `.limit()` call, which is where the
// query-builder chain in hospitalSearch.ts terminates.
const { limitMock } = vi.hoisted(() => ({ limitMock: vi.fn() }));

vi.mock("./supabaseClient", () => {
  const builder = {
    select: vi.fn(() => builder),
    ilike: vi.fn(() => builder),
    order: vi.fn(() => builder),
    limit: limitMock,
  };
  return {
    supabase: {
      from: vi.fn(() => builder),
    },
  };
});

import { normalizeSearchTerm, searchHospitalsByName } from "./hospitalSearch";

describe("normalizeSearchTerm", () => {
  it("trims surrounding whitespace", () => {
    expect(normalizeSearchTerm("  Anson General  ")).toBe("Anson General");
  });

  it("returns an empty string for undefined input", () => {
    expect(normalizeSearchTerm(undefined)).toBe("");
  });
});

describe("searchHospitalsByName", () => {
  it("returns matching hospitals on the happy path", async () => {
    limitMock.mockResolvedValueOnce({
      data: [
        { provider_ccn: "670781", name: "ANSON GENERAL HOSPITAL", state: "TX" },
      ],
      error: null,
    });

    const result = await searchHospitalsByName("Anson");

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.hospitals).toHaveLength(1);
      expect(result.hospitals[0].name).toBe("ANSON GENERAL HOSPITAL");
    }
  });

  it("returns an empty list, not an error, when nothing matches (not-found path)", async () => {
    limitMock.mockResolvedValueOnce({ data: [], error: null });

    const result = await searchHospitalsByName("Nonexistent Hospital Zzz");

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.hospitals).toEqual([]);
    }
  });

  it("surfaces a data-retrieval error instead of throwing (failure path)", async () => {
    limitMock.mockResolvedValueOnce({
      data: null,
      error: { message: "connection timeout" },
    });

    const result = await searchHospitalsByName("Anson");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe("connection timeout");
    }
  });
});
