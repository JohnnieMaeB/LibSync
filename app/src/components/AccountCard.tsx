import type { AccountSummaryData } from "../types";

// Tier 9 Phase 38: the signed-in patron's own account, from the library's ILS.
// These titles are library records; they're shown here, on the patron's own
// screen, and are never sent to the AI model.

function Section({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="account-card-section">
      <h3>
        {title} ({items.length})
      </h3>
      {items.length > 0 ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>None</p>
      )}
    </div>
  );
}

export function AccountCard({ data }: { data: AccountSummaryData }) {
  const { items, fees, message } = data;
  return (
    <section className="account-card" aria-label="Your library account">
      <Section title="Checked out" items={items.charged ?? []} />
      <Section title="Overdue" items={items.overdue ?? []} />
      <Section title="On hold" items={items.holds ?? []} />
      {fees && Number(fees) > 0 && <p className="account-card-fees">Fees owed: ${fees}</p>}
      {message && <p className="account-card-message">{message}</p>}
    </section>
  );
}
