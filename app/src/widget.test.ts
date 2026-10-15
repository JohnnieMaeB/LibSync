import { describe, expect, it } from "vitest";
import { getWidgetConfig, safeHelpUrl } from "./widget";

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

  it("parses the help URL and tool groups loader.js forwards", () => {
    const config = getWidgetConfig("?mode=widget&help=mailto%3Aask%40lib.example&tools=+catalog+");
    expect(config.helpUrl).toBe("mailto:ask@lib.example");
    expect(config.tools).toBe("catalog");
  });

  it("defaults help URL and tools to null", () => {
    const config = getWidgetConfig("?mode=widget");
    expect(config.helpUrl).toBeNull();
    expect(config.tools).toBeNull();
  });
});

describe("safeHelpUrl", () => {
  it.each(["https://lib.example/ask", "http://lib.example", "mailto:a@b.example", "tel:+15555550100"])(
    "accepts %s",
    (url) => {
      expect(safeHelpUrl(url)).not.toBeNull();
    },
  );

  it.each(["javascript:alert(1)", "data:text/html,hi", "not a url", "", null])("rejects %s", (url) => {
    expect(safeHelpUrl(url)).toBeNull();
  });
});
