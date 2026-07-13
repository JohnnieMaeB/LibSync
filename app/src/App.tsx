import { useState } from "react";
import { Header } from "./components/Header";
import { CapabilityLine } from "./components/CapabilityLine";
import { ChatBox } from "./components/ChatBox";
import { Composer } from "./components/Composer";
import { AppShell } from "./components/AppShell";
import { useAgentStream } from "./hooks/useAgentStream";
import { useConversations } from "./hooks/useConversations";
import type { ChatEntry } from "./types";

// Owns one conversation's live chat state. Keyed by conversationId in
// App() below, so switching conversations remounts this (resetting
// Composer's draft text and any other local UI state for free) instead of
// needing bespoke reset logic.
function ChatConversation({
  conversationId,
  initialEntries,
  onEntriesChange,
}: {
  conversationId: string;
  initialEntries: ChatEntry[];
  onEntriesChange: (conversationId: string, entries: ChatEntry[]) => void;
}) {
  const [capabilityDismissed, setCapabilityDismissed] = useState(false);
  const { entries, isStreaming, sendMessage, regenerate, retry, stop } = useAgentStream({
    conversationId,
    initialEntries,
    onEntriesChange,
  });
  const chipsHidden = entries.length > 0;

  return (
    <>
      <Header />
      <CapabilityLine dismissed={capabilityDismissed} onDismiss={() => setCapabilityDismissed(true)} />
      <ChatBox
        entries={entries}
        chipsHidden={chipsHidden}
        onSelectSuggestion={sendMessage}
        onRegenerate={regenerate}
        onRetry={retry}
      />
      <Composer isStreaming={isStreaming} onSend={sendMessage} onStop={stop} />
    </>
  );
}

export default function App() {
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
        />
      </div>
    </AppShell>
  );
}
