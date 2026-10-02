import { describe, expect, it } from "vitest";
import { getWidgetConfig } from "./widget";

describe("getWidgetConfig", () => {
  it("is not widget mode when mode=widget is absent from the URL", () => {
    expect(getWidgetConfig("").isWidget).toBe(false);
    expect(getWidgetConfig("?foo=bar").isWidget).toBe(false);
  });

  it("detects widget mode from ?mode=widget", () => {
    expect(getWidgetConfig("?mode=widget").isWidget).toBe(true);
  });

  it("ignores any other mode value", () => {
    expect(getWidgetConfig("?mode=standalone").isWidget).toBe(false);
  });

  it("parses the library id loader.js forwards as a query param", () => {
    const config = getWidgetConfig("?mode=widget&library=acme-library");
    expect(config.isWidget).toBe(true);
    expect(config.libraryId).toBe("acme-library");
  });

  it("libraryId is null when not present", () => {
    expect(getWidgetConfig("?mode=widget").libraryId).toBeNull();
  });
});
