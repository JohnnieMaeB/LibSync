export function SourceBadge({ number }: { number: number }) {
  return (
    <span className="source-badge" aria-label={`Source ${number}`}>
      {number}
    </span>
  );
}
