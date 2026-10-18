import { useCallback, useState } from "react";
import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import type { ConversationSummary } from "../types";
import { useI18n } from "../i18n";

export function AppShell({
  compact = false,
  conversations,
  activeId,
  onNewChat,
  onSelectConversation,
  onRenameConversation,
  onDeleteConversation,
  sidebarFooter,
  children,
}: {
  compact?: boolean;
  conversations: ConversationSummary[];
  activeId: string | null;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
  onDeleteConversation: (id: string) => void;
  // Tier 9: the optional patron account panel.
  sidebarFooter?: ReactNode;
  children: ReactNode;
}) {
  const { t } = useI18n();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);

  useKeyboardShortcuts({ onNewChat, onEscape: closeSidebar });

  // Compact mode is the original fixed 420px widget card — kept as an
  // explicit opt-in so Tier 6's embeddable widget can reuse it directly,
  // per TIER5_PLAN.md §3.
  if (compact) {
    return <div className="app-shell compact">{children}</div>;
  }

  return (
    <div className="app-shell">
      <button
        type="button"
        className="sidebar-open-toggle"
        aria-label={t.openSidebar}
        onClick={() => setSidebarOpen(true)}
      >
        ☰
      </button>
      <div className={`sidebar-overlay${sidebarOpen ? " open" : ""}`} onClick={closeSidebar} />
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        collapsed={collapsed}
        open={sidebarOpen}
        onToggleCollapse={() => setCollapsed((c) => !c)}
        onClose={closeSidebar}
        onNewChat={onNewChat}
        onSelect={onSelectConversation}
        onRename={onRenameConversation}
        onDelete={onDeleteConversation}
        footer={sidebarFooter}
      />
      <div className="main-column">{children}</div>
    </div>
  );
}
