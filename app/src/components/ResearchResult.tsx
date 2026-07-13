import type { NumberedWork } from "../types";
import { ScholarlyWorkCard } from "./ScholarlyWorkCard";

export function ResearchResult({ intro, works }: { intro?: string; works: NumberedWork[] }) {
  return (
    <div className="research-result">
      {intro && <div className="research-result-intro">{intro}</div>}
      {works.map(({ number, data }) => (
        <ScholarlyWorkCard key={number} data={data} number={number} />
      ))}
    </div>
  );
}
