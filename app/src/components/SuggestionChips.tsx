// Teaches the assistant's range (library policies, catalog/research/citation
// tools) without a manual — clicking a chip fills the input and sends it.
const SUGGESTED_PROMPTS = [
  "Find me a sci-fi audiobook",
  "How do I renew a book?",
  "Cite this paper in APA",
  "What are your library card policies?",
];

export function SuggestionChips({ hidden, onSelect }: { hidden: boolean; onSelect: (prompt: string) => void }) {
  return (
    <div className={`suggestion-chips${hidden ? " hidden" : ""}`}>
      {SUGGESTED_PROMPTS.map((prompt) => (
        <button key={prompt} type="button" className="suggestion-chip" onClick={() => onSelect(prompt)}>
          {prompt}
        </button>
      ))}
    </div>
  );
}
