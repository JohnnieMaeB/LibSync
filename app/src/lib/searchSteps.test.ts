import { describe, expect, it } from "vitest";
import { describeStep, stepFromToolCall } from "./searchSteps";
import { en, es } from "../i18n/messages";

describe("search steps", () => {
  it("describes each search in plain words, in the interface language", () => {
    const step = stepFromToolCall("search_library_policies", '{"query": "renewals"}')!;
    expect(describeStep(step, en)).toBe("Searched this library's policies for “renewals”");
    expect(describeStep(step, es)).toBe("Busqué “renewals” en las normas de esta biblioteca");
  });

  it("tells read-alikes from topic recommendations", () => {
    expect(describeStep(stepFromToolCall("recommend_books", '{"like": "Beloved"}')!, en)).toContain("share subjects with “Beloved”");
    expect(describeStep(stepFromToolCall("recommend_books", '{"about": "dragons"}')!, en)).toContain("books about “dragons”");
  });

  it("skips the output tool and invented tool names, and survives bad arguments", () => {
    expect(stepFromToolCall("final_result", "{}")).toBeNull();
    expect(stepFromToolCall("json", "{}")).toBeNull();
    expect(stepFromToolCall("search_catalog", "{not json")).toEqual({ tool: "search_catalog", query: "", mode: undefined });
  });
});
