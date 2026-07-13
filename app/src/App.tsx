import { useState } from "react";
import { Header } from "./components/Header";
import { CapabilityLine } from "./components/CapabilityLine";
import { ChatBox } from "./components/ChatBox";
import { Composer } from "./components/Composer";
import { useAgentStream } from "./hooks/useAgentStream";

export default function App() {
  const [capabilityDismissed, setCapabilityDismissed] = useState(false);
  const { entries, isStreaming, sendMessage, regenerate, retry, stop } = useAgentStream();
  const chipsHidden = entries.length > 0;

  return (
    <div className="container">
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
    </div>
  );
}
