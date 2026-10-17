import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Header } from "./components/Header";
import { CapabilityLine } from "./components/CapabilityLine";
import { AiNotice } from "./components/AiNotice";
import { ChatBox } from "./components/ChatBox";
import { Composer } from "./components/Composer";
import { AppShell } from "./components/AppShell";
import { useAgentStream } from "./hooks/useAgentStream";
import { useConversations } from "./hooks/useConversations";
import { generateId } from "./lib/id";
import { getWidgetConfig, standaloneHelpUrl, type WidgetConfig } from "./widget";
import { useLibraryConfig } from "./libraryConfig";

// Loaded only when a staff member opens #/admin, so the patron app never
// downloads the dashboard or the Supabase client.
const AdminApp = lazy(() => import("./admin/AdminApp"));
import type { ChatEntry } from "./types";
import { API_BASE_URL } from "./config";
import { blocksToPlainText } from "./lib/plainText";

// Owns one conversation's live chat state. Keyed by conversationId in
// App() below, so switching conversations remounts this (resetting
// Composer's draft text and any other local UI state for free) instead of
// needing bespoke reset logic.
function ChatConversation({
  conversationId,
  initialEntries,
  onEntriesChange,
  libraryId,
  tools,
  helpUrl,
  feedbackEnabled = false,
  onClose,
}: {
  conversationId: string;
  initialEntries: ChatEntry[];
  onEntriesChange: (conversationId: string, entries: ChatEntry[]) => void;
  libraryId?: string | null;
  tools?: string | null;
  helpUrl: string | null;
  feedbackEnabled?: boolean;
  onClose?: () => void;
}) {
  const [capabilityDismissed, setCapabilityDismissed] = useState(false);
  const { entries, isStreaming, sendMessage, regenerate, retry, stop } = useAgentStream({
    conversationId,
    initialEntries,
    onEntriesChange,
    libraryId,
    tools,
  });
  const chipsHidden = entries.length > 0;

  // Phase 34: send one exchange (the reply and the question just before it)
  // to the library's feedback webhook, only after the patron asks to.
  const sendFeedback = useCallback(
    async (botId: string) => {
      const index = entries.findIndex((e) => e.id === botId);
      const bot = entries[index];
      const question = entries
        .slice(0, index)
        .reverse()
        .find((e) => e.kind === "user");
      if (!bot || bot.kind !== "bot" || !question || question.kind !== "user" || !libraryId) return false;
      try {
        const response = await fetch(`${API_BASE_URL}/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-LibSync-Library": libraryId },
          body: JSON.stringify({ question: question.text, answer: blocksToPlainText(bot.blocks) }),
        });
        return response.ok;
      } catch {
        return false;
      }
    },
    [entries, libraryId],
  );

  return (
    <>
      <Header onClose={onClose} />
      <CapabilityLine dismissed={capabilityDismissed} onDismiss={() => setCapabilityDismissed(true)} />
      <ChatBox
        entries={entries}
        chipsHidden={chipsHidden}
        onSelectSuggestion={sendMessage}
        onRegenerate={regenerate}
        onRetry={retry}
        onFeedback={feedbackEnabled ? sendFeedback : undefined}
      />
      <Composer isStreaming={isStreaming} onSend={sendMessage} onStop={stop} />
      <AiNotice helpUrl={helpUrl} />
    </>
  );
}

// Widget mode (Tier 6): a single ephemeral conversation, no IndexedDB
// history, rendered through AppShell's `compact` card — see
// TIER6_PLAN.md §2/§3 and AppShell.tsx's `compact` prop, built in Tier 5
// specifically for this reuse.
// Shown instead of the chat when the library switched the assistant off in its
// dashboard (TIER8_PLAN.md §2.8: the library can disable AI features).
function AssistantOff({ helpUrl, onClose }: { helpUrl: string | null; onClose: () => void }) {
  return (
    <>
      <Header onClose={onClose} />
      <div className="assistant-off" role="status">
        <p>This library has turned the AI assistant off.</p>
        {helpUrl ? (
          <a href={helpUrl} target="_blank" rel="noopener noreferrer">
            Talk to a librarian
          </a>
        ) : (
          <p>Please contact library staff for help.</p>
        )}
      </div>
    </>
  );
}

function WidgetApp({ config }: { config: WidgetConfig }) {
  const library = useLibraryConfig(config.libraryId);
  // Dashboard settings win over the snippet's, so a library can change its
  // help link without editing its website.
  const helpUrl = library?.helpUrl ?? config.helpUrl;
  const [conversationId] = useState(() => generateId());
  const noopPersist = useCallback(() => {}, []);
  const handleClose = useCallback(() => {
    window.parent.postMessage({ type: "libsync:close" }, "*");
  }, []);

  return (
    <AppShell
      compact
      conversations={[]}
      activeId={conversationId}
      onNewChat={() => {}}
      onSelectConversation={() => {}}
      onRenameConversation={() => {}}
      onDeleteConversation={() => {}}
    >
      <div className="container">
        {library && !library.aiEnabled ? (
          <AssistantOff helpUrl={helpUrl} onClose={handleClose} />
        ) : (
          <ChatConversation
            conversationId={conversationId}
            initialEntries={[]}
            onEntriesChange={noopPersist}
            libraryId={config.libraryId}
            tools={config.tools}
            helpUrl={helpUrl}
            feedbackEnabled={library?.feedbackEnabled ?? false}
            onClose={handleClose}
          />
        )}
      </div>
    </AppShell>
  );
}

function StandaloneApp() {
  const {
    conversations,
    activeId,
    activeEntries,
    createConversation,
    selectConversation,
    renameConversation,
    removeConversation,
    persistActiveEntries,
  } = useConversations();

  return (
    <AppShell
      conversations={conversations}
      activeId={activeId}
      onNewChat={createConversation}
      onSelectConversation={selectConversation}
      onRenameConversation={renameConversation}
      onDeleteConversation={removeConversation}
    >
      <div className="container">
        <ChatConversation
          key={activeId}
          conversationId={activeId}
          initialEntries={activeEntries}
          onEntriesChange={persistActiveEntries}
          helpUrl={standaloneHelpUrl()}
        />
      </div>
    </AppShell>
  );
}

export default function App() {
  // Computed once per mount — the URL doesn't change without a reload, so
  // this never needs to be reactive, and the widget/standalone branch below
  // stays stable across a given component instance's lifetime (satisfying
  // React's rules of hooks).
  const [widgetConfig] = useState(() => getWidgetConfig());
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  if (!widgetConfig.isWidget && hash.startsWith("#/admin")) {
    return (
      <Suspense fallback={<p className="admin-loading">Loading dashboard…</p>}>
        <AdminApp />
      </Suspense>
    );
  }
  if (widgetConfig.isWidget) {
    return <WidgetApp config={widgetConfig} />;
  }
  return <StandaloneApp />;
}
