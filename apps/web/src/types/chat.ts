export type MessageRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id: string;
  conversationId: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  status?: "streaming" | "complete" | "error";
};

export type Conversation = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageIds: string[];
  pinned?: boolean;
};

export type ChatRequest = {
  conversationId: string;
  messages: Pick<ChatMessage, "role" | "content">[];
  memory?: MemorySnapshot;
  tools?: ToolName[];
};

export type MemorySnapshot = {
  shortTerm: string[];
  longTerm: MemoryRecord[];
};

export type MemoryRecord = {
  id: string;
  content: string;
  createdAt: string;
  tags: readonly string[];
};

export type ToolName = "web_search" | "calculator" | "file_reader";
