import type { ReactNode } from "react";
import type { ConversationSummary } from "../types";
import { SidebarConversationItem } from "./SidebarConversationItem";
import { useI18n } from "../i18n";

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
  footer,
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
  footer?: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <nav className={`sidebar${collapsed ? " collapsed" : ""}${open ? " open" : ""}`} aria-label={t.conversations}>
      <div className="sidebar-header">
        <button type="button" className="sidebar-new-chat" onClick={onNewChat}>
          <span aria-hidden="true">+</span>
          <span className="sidebar-label">{t.newChat}</span>
        </button>
        <button
          type="button"
          className="sidebar-collapse-toggle"
          onClick={onToggleCollapse}
          aria-label={collapsed ? t.expandSidebar : t.collapseSidebar}
        >
          {collapsed ? "»" : "«"}
        </button>
        <button type="button" className="sidebar-close" onClick={onClose} aria-label={t.closeSidebar}>
          &times;
        </button>
      </div>
      {conversations.length === 0 ? (
        <p className="sidebar-empty">{t.noConversations}</p>
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
      {footer && !collapsed && <div className="sidebar-footer">{footer}</div>}
    </nav>
  );
}
