import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CapacityPanel } from "./CapacityPanel";

afterEach(() => vi.unstubAllGlobals());

function respondWith(body: unknown, ok = true) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok, json: async () => body }));
}

describe("AI capacity panel", () => {
  it("shows the status and each model's budget", async () => {
    respondWith({
      status: "low",
      primary_model: "openai/gpt-oss-120b",
      models: [
        {
          model: "openai/gpt-oss-120b",
          requests_per_day: 1000,
          requests_left_today: 80,
          requests_reset_in: "3h2m",
          updated_seconds_ago: 5,
          throttled_last_hour: 0,
        },
        { model: "qwen/qwen3.8-27b", updated_seconds_ago: null, throttled_last_hour: 2 },
      ],
    });
    render(<CapacityPanel />);
    expect(await screen.findByText(/running low today/)).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "openai/gpt-oss-120b (main)" })).toBeInTheDocument();
    expect(screen.getByText("80 of 1000")).toBeInTheDocument();
    expect(screen.getAllByText("Not reported")).toHaveLength(2);
  });

  it("says so when the numbers can't be loaded", async () => {
    respondWith({ detail: "nope" }, false);
    render(<CapacityPanel />);
    expect(await screen.findByText("Couldn't load AI capacity.")).toBeInTheDocument();
  });
});
