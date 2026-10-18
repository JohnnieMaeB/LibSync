import type { WorkCardData } from "../types";
import { SourceBadge } from "./SourceBadge";
import { useI18n } from "../i18n";

export function ScholarlyWorkCard({ data, number }: { data: WorkCardData; number: number }) {
  const { t } = useI18n();
  const { title, authors, year, doi, citationCount, isOa, abstract } = data;
  const titleText = year ? `${title} (${year})` : title;

  return (
    <div className="work-card">
      <SourceBadge number={number} />
      {doi ? (
        <a className="work-card-title" href={doi} target="_blank" rel="noopener noreferrer">
          {titleText}
        </a>
      ) : (
        <div className="work-card-title">{titleText}</div>
      )}
      <div className="work-card-authors">{authors}</div>
      <div className="work-card-meta">
        <span className="work-card-citations">
          {t.citations(citationCount)}
        </span>
        <span className={`work-card-oa work-card-oa--${isOa ? "open" : "closed"}`}>
          {isOa ? t.openAccess : t.notOpenAccess}
        </span>
      </div>
      {abstract && (
        <details className="work-card-abstract">
          <summary>{t.abstract}</summary>
          <p>{abstract}</p>
        </details>
      )}
    </div>
  );
}
