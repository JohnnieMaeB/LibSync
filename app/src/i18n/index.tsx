import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { en, es, type Messages } from "./messages";

export const LANGUAGES = { en: "English", es: "Español" } as const;
export type Language = keyof typeof LANGUAGES;

const MESSAGES: Record<Language, Messages> = { en, es };
const STORAGE_KEY = "libsync:lang";

function supported(code: string | null | undefined): Language | null {
  const base = code?.trim().toLowerCase().split("-")[0];
  return base && base in LANGUAGES ? (base as Language) : null;
}

// Which language to show first: an explicit ?lang= (the widget passes the
// library's data-lang, or its website's own <html lang>), then the patron's
// own earlier choice, then their browser's languages, then English.
export function pickLanguage(
  search: string = window.location.search,
  browserLanguages: readonly string[] = navigator.languages ?? [navigator.language],
): Language {
  const fromUrl = supported(new URLSearchParams(search).get("lang"));
  if (fromUrl) return fromUrl;
  try {
    const stored = supported(localStorage.getItem(STORAGE_KEY));
    if (stored) return stored;
  } catch {
    // Storage blocked (private mode, sandboxed iframe): fall through.
  }
  for (const language of browserLanguages) {
    const match = supported(language);
    if (match) return match;
  }
  return "en";
}

interface I18n {
  lang: Language;
  t: Messages;
  setLang: (lang: Language) => void;
}

// English without a provider, so components render the same in isolation
// (tests, the staff dashboard) as they always have.
const I18nContext = createContext<I18n>({ lang: "en", t: en, setLang: () => {} });

export function I18nProvider({ initial, children }: { initial?: Language; children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => initial ?? pickLanguage());

  // WCAG 3.1.1 (Language of Page): screen readers pick their voice from this.
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((next: Language) => {
    setLangState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Not remembered across visits; still switches now.
    }
  }, []);

  const value = useMemo(() => ({ lang, t: MESSAGES[lang], setLang }), [lang, setLang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  return useContext(I18nContext);
}

export function LanguagePicker() {
  const { lang, t, setLang } = useI18n();
  return (
    <select
      className="language-picker"
      aria-label={t.languageLabel}
      value={lang}
      onChange={(event) => setLang(event.target.value as Language)}
    >
      {Object.entries(LANGUAGES).map(([code, name]) => (
        // Each name in its own language, marked so it's pronounced right.
        <option key={code} value={code} lang={code}>
          {name}
        </option>
      ))}
    </select>
  );
}
