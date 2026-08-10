export interface BookCardData {
  title: string;
  author: string;
  year?: string | number;
  availability: string;
  coverUrl?: string;
  url?: string;
}

export interface WorkCardData {
  title: string;
  authors: string;
  year?: string | number;
  doi?: string;
  citationCount: number;
  isOa: boolean;
  abstract?: string;
}

export interface NumberedWork {
  number: number;
  data: WorkCardData;
}

export interface CitationCardData {
  formatted: string;
  doi?: string;
  style?: string;
  availableStyles?: string[];
}

export type Block =
  | { type: "text"; key: string; text: string }
  | { type: "book"; key: string; number: number; data: BookCardData }
  | { type: "research"; key: string; intro?: string; works: NumberedWork[] }
  | { type: "citation"; key: string; number: number; data: CitationCardData };

export type BotStatus = "loading" | "tool" | "streaming" | "done" | "error" | "stopped";

export interface BotEntry {
  kind: "bot";
  id: string;
  status: BotStatus;
  toolLabel?: string;
  blocks: Block[];
  cardCount: number;
  errorText?: string;
  isLatest: boolean;
}

export interface UserEntry {
  kind: "user";
  id: string;
  text: string;
}

export type ChatEntry = UserEntry | BotEntry;
