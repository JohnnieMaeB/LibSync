import { useState } from "react";
import type { KeyboardEvent } from "react";
import type { ConversationSummary } from "../types";
import { useI18n } from "../i18n";

export function SidebarConversationItem({
  conversation,
  active,
  onSelect,
  onRename,
  onDelete,
}: {
  conversation: ConversationSummary;
  active: boolean;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
}) {
  const { t } = useI18n();
  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState(conversation.title);

  const startEditing = () => {
    setDraftTitle(conversation.title);
    setEditing(true);
  };

  const commitEditing = () => {
    const trimmed = draftTitle.trim();
    if (trimmed && trimmed !== conversation.title) onRename(conversation.id, trimmed);
    setEditing(false);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      commitEditing();
    } else if (e.key === "Escape") {
      e.preventDefault();
      setEditing(false);
    }
  };

  return (
    <li className={active ? "active" : ""}>
      <div className="sidebar-conversation">
        {editing ? (
          <input
            className="sidebar-conversation-rename-input"
            value={draftTitle}
            autoFocus
            onChange={(e) => setDraftTitle(e.target.value)}
            onBlur={commitEditing}
            onKeyDown={handleKeyDown}
            aria-label={t.conversationTitle}
          />
        ) : (
          <button
            type="button"
            className="sidebar-conversation-title"
            onClick={() => onSelect(conversation.id)}
            onDoubleClick={startEditing}
          >
            {conversation.title}
          </button>
        )}
        <div className="sidebar-conversation-actions">
          <button
            type="button"
            className="sidebar-conversation-action-btn"
            aria-label={t.rename(conversation.title)}
            onClick={startEditing}
          >
            ✎
          </button>
          <button
            type="button"
            className="sidebar-conversation-action-btn"
            aria-label={t.delete(conversation.title)}
            onClick={() => {
              if (window.confirm(t.confirmDelete(conversation.title))) onDelete(conversation.id);
            }}
          >
            🗑
          </button>
        </div>
      </div>
    </li>
  );
}
