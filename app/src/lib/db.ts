import { openDB } from "idb";
import type { DBSchema, IDBPDatabase } from "idb";
import type { Conversation } from "../types";

interface LibSyncDB extends DBSchema {
  conversations: {
    key: string;
    value: Conversation;
    indexes: { "by-updatedAt": number };
  };
}

const DB_NAME = "libsync";
const DB_VERSION = 1;
const STORE_NAME = "conversations";

let dbPromise: Promise<IDBPDatabase<LibSyncDB>> | null = null;

function getDB(): Promise<IDBPDatabase<LibSyncDB>> {
  if (!dbPromise) {
    dbPromise = openDB<LibSyncDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("by-updatedAt", "updatedAt");
      },
    });
  }
  return dbPromise;
}

// Newest-first, matching the sidebar's ordering (TIER5_PLAN.md §2).
export async function listConversations(): Promise<Conversation[]> {
  const db = await getDB();
  const all = await db.getAllFromIndex(STORE_NAME, "by-updatedAt");
  return all.reverse();
}

export async function getConversation(id: string): Promise<Conversation | undefined> {
  const db = await getDB();
  return db.get(STORE_NAME, id);
}

export async function putConversation(conversation: Conversation): Promise<void> {
  const db = await getDB();
  await db.put(STORE_NAME, conversation);
}

export async function deleteConversation(id: string): Promise<void> {
  const db = await getDB();
  await db.delete(STORE_NAME, id);
}
