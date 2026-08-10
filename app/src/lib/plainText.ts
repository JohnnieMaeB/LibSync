import type { Block } from "../types";

// Approximates the original DOM-clone-and-strip-badges textContent extraction
// (getMessagePlainText in client/src/script.js) from structured block data,
// for the message-actions "Copy" button.
export function blocksToPlainText(blocks: Block[]): string {
  return blocks
    .map((block) => {
      if (block.type === "text") return block.text;
      if (block.type === "book") {
        const { title, author, year, availability } = block.data;
        const titleText = year ? `${title} (${year})` : title;
        return `${titleText}by ${author}${availability}`;
      }
      if (block.type === "citation") {
        return block.data.formatted;
      }
      // research
      const intro = block.intro || "";
      const works = block.works
        .map(({ data }) => {
          const titleText = data.year ? `${data.title} (${data.year})` : data.title;
          return `${titleText}${data.authors}`;
        })
        .join("");
      return `${intro}${works}`;
    })
    .join("");
}
