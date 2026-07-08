"use client";

import { ChatPanel } from "@/components/chat/chat-panel";
import { ConversationSidebar } from "@/components/chat/conversation-sidebar";

export default function ChatPage() {
  return (
    <div className="flex h-[calc(100dvh-3.5rem)]">
      <ConversationSidebar />
      <ChatPanel />
    </div>
  );
}
