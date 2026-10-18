import type { BookCardData } from "../types";
import { SourceBadge } from "./SourceBadge";
import { useI18n } from "../i18n";

// Renders one book as a real card from data (title, author, availability,
// cover image, and an Open Library link-out) instead of prose.
export function BookCard({ data, number }: { data: BookCardData; number: number }) {
  const { t } = useI18n();
  const { title, author, year, availability, coverUrl, url } = data;
  const availabilityClass = `book-card-availability--${availability.trim().replace(/\s+/g, "-")}`;
  const titleText = year ? `${title} (${year})` : title;

  return (
    <div className="book-card">
      <SourceBadge number={number} />
      {coverUrl && <img className="book-card-cover" src={coverUrl} alt={t.coverOf(title)} />}
      <div className="book-card-body">
        {url ? (
          <a className="book-card-title" href={url} target="_blank" rel="noopener noreferrer">
            {titleText}
          </a>
        ) : (
          <div className="book-card-title">{titleText}</div>
        )}
        <div className="book-card-author">{t.byAuthor(author)}</div>
        <span className={`book-card-availability ${availabilityClass}`}>{t.availability[availability.trim()] ?? availability}</span>
      </div>
    </div>
  );
}
