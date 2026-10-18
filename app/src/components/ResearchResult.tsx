import type { NumberedWork } from "../types";
import { ScholarlyWorkCard } from "./ScholarlyWorkCard";
import { useI18n } from "../i18n";

export function ResearchResult({ intro, works }: { intro?: string; works: NumberedWork[] }) {
  const { t } = useI18n();
  return (
    <div className="research-result">
      {intro && <div className="research-result-intro">{intro}</div>}
      {works.map(({ number, data }) => (
        <ScholarlyWorkCard key={number} data={data} number={number} />
      ))}
      {/* RUSA: help patrons evaluate what they find, not just find it. */}
      {works.length > 0 && (
        <details className="evaluate-sources">
          <summary>{t.evaluateHeading}</summary>
          <ul>
            {t.evaluateItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
