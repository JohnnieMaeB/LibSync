import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { I18nProvider, pickLanguage } from ".";
import { en, es } from "./messages";
import { Header } from "../components/Header";
import { Composer } from "../components/Composer";

afterEach(() => {
  localStorage.clear();
  document.documentElement.lang = "en";
});

describe("pickLanguage", () => {
  it("prefers ?lang=, then the saved choice, then the browser, then English", () => {
    expect(pickLanguage("?lang=es-MX", ["en-US"])).toBe("es");
    localStorage.setItem("libsync:lang", "es");
    expect(pickLanguage("", ["en-US"])).toBe("es");
    localStorage.clear();
    expect(pickLanguage("", ["fr-CA", "es-419"])).toBe("es");
    expect(pickLanguage("?lang=xx", ["de"])).toBe("en");
  });
});

describe("Spanish interface", () => {
  it("has a translation for every English string", () => {
    // The type already requires it; this also catches empty strings.
    for (const key of Object.keys(en) as (keyof typeof en)[]) {
      expect(es[key], key).toBeTruthy();
    }
    expect(es.suggestions).toHaveLength(en.suggestions.length);
    expect(es.privacyItems).toHaveLength(en.privacyItems.length);
  });

  it("renders in Spanish, sets the page language, and switches back from the picker", async () => {
    render(
      <I18nProvider initial="es">
        <Header />
        <Composer isStreaming={false} onSend={() => {}} onStop={() => {}} />
      </I18nProvider>,
    );
    expect(screen.getByText(es.tagline)).toBeInTheDocument();
    expect(screen.getByLabelText(es.composerLabel)).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("es");

    await userEvent.selectOptions(screen.getByLabelText(es.languageLabel), "en");
    expect(screen.getByText(en.tagline)).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
    expect(localStorage.getItem("libsync:lang")).toBe("en");
  });
});
