import { useI18n } from "../i18n";

// Teaches the assistant's range (library policies, catalog/research/citation
// tools) without a manual — clicking a chip fills the input and sends it.

export function SuggestionChips({ hidden, onSelect }: { hidden: boolean; onSelect: (prompt: string) => void }) {
  const { t } = useI18n();
  return (
    <div className={`suggestion-chips${hidden ? " hidden" : ""}`}>
      {t.suggestions.map((prompt) => (
        <button key={prompt} type="button" className="suggestion-chip" onClick={() => onSelect(prompt)}>
          {prompt}
        </button>
      ))}
    </div>
  );
}
