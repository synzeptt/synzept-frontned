import { AgentAction } from "./types";

export function extractJson(raw: string): string {
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start === -1 || end === -1) {
    return raw;
  }
  return raw.slice(start, end + 1);
}

export function tryParseJson<T>(raw: string): T | null {
  try {
    return JSON.parse(extractJson(raw)) as T;
  } catch {
    return null;
  }
}

export function normalizeText(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[\W_]+/g, " ")
    .split(" ")
    .filter(Boolean);
}

export function isValidIsoDate(value: string | undefined): boolean {
  if (!value) {
    return false;
  }
  const date = new Date(value);
  return !Number.isNaN(date.getTime());
}

export function parseDateString(value: string | undefined): string | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) {
    return date.toISOString();
  }
  return null;
}

export function buildActionConfirmation(action: AgentAction): string {
  switch (action.type) {
    case "task":
      return action.title
        ? `Done. I've added "${action.title}" to your task list.`
        : "Done. I created a new task for you.";
    case "note":
      return action.title
        ? `Noted. I've saved "${action.title}" in your notes.`
        : "Noted. I've saved that idea to your notes.";
    case "reminder":
      return action.details
        ? `Reminder set. I will remind you to ${action.details}${action.dueAt ? ` at ${new Date(action.dueAt).toLocaleString()}` : ""}.`
        : "Reminder set. I will remind you when it is due.";
    case "query":
      return "Got it. Here is what I found.";
    default:
      return "";
  }
}
