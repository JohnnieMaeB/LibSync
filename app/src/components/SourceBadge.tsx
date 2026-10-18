import { useI18n } from "../i18n";

export function SourceBadge({ number }: { number: number }) {
  const { t } = useI18n();
  return (
    <span className="source-badge" aria-label={t.source(number)}>
      {number}
    </span>
  );
}
