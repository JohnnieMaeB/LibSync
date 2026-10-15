import { useCallback, useState } from "react";
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
import type { ChatEntry } from "./types";

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
  onClose,
}: {
  conversationId: string;
  initialEntries: ChatEntry[];
  onEntriesChange: (conversationId: string, entries: ChatEntry[]) => void;
  libraryId?: string | null;
  tools?: string | null;
  helpUrl: string | null;
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
function WidgetApp({ config }: { config: WidgetConfig }) {
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
        <ChatConversation
          conversationId={conversationId}
          initialEntries={[]}
          onEntriesChange={noopPersist}
          libraryId={config.libraryId}
          tools={config.tools}
          helpUrl={config.helpUrl}
          onClose={handleClose}
        />
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

  if (widgetConfig.isWidget) {
    return <WidgetApp config={widgetConfig} />;
  }
  return <StandaloneApp />;
}
