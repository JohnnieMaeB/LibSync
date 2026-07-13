import type { WorkCardData } from "../types";
import { SourceBadge } from "./SourceBadge";

export function ScholarlyWorkCard({ data, number }: { data: WorkCardData; number: number }) {
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
          {citationCount} citation{citationCount === 1 ? "" : "s"}
        </span>
        <span className={`work-card-oa work-card-oa--${isOa ? "open" : "closed"}`}>
          {isOa ? "Open access" : "Not open access"}
        </span>
      </div>
      {abstract && (
        <details className="work-card-abstract">
          <summary>Abstract</summary>
          <p>{abstract}</p>
        </details>
      )}
    </div>
  );
}
