import type { ConversationSummary } from "../types";
import { SidebarConversationItem } from "./SidebarConversationItem";

export function Sidebar({
  conversations,
  activeId,
  collapsed,
  open,
  onToggleCollapse,
  onClose,
  onNewChat,
  onSelect,
  onRename,
  onDelete,
}: {
  conversations: ConversationSummary[];
  activeId: string | null;
  collapsed: boolean;
  open: boolean;
  onToggleCollapse: () => void;
  onClose: () => void;
  onNewChat: () => void;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <nav className={`sidebar${collapsed ? " collapsed" : ""}${open ? " open" : ""}`} aria-label="Conversations">
      <div className="sidebar-header">
        <button type="button" className="sidebar-new-chat" onClick={onNewChat}>
          <span aria-hidden="true">+</span>
          <span className="sidebar-label">New chat</span>
        </button>
        <button
          type="button"
          className="sidebar-collapse-toggle"
          onClick={onToggleCollapse}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? "»" : "«"}
        </button>
        <button type="button" className="sidebar-close" onClick={onClose} aria-label="Close sidebar">
          &times;
        </button>
      </div>
      {conversations.length === 0 ? (
        <p className="sidebar-empty">No conversations yet.</p>
      ) : (
        <ul className="sidebar-conversations">
          {conversations.map((conversation) => (
            <SidebarConversationItem
              key={conversation.id}
              conversation={conversation}
              active={conversation.id === activeId}
              onSelect={onSelect}
              onRename={onRename}
              onDelete={onDelete}
            />
          ))}
        </ul>
      )}
    </nav>
  );
}
