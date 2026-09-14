export type ActivityCategory = "all" | "files" | "ai" | "conversations" | "search" | "connected-apps" | "system";

export type ActivityStatus = "completed" | "running" | "failed" | "cancelled";

export type ActivityItem = {
  id: string;
  type: string;
  category: ActivityCategory | string;
  title: string;
  description: string;
  timestamp: string;
  status: ActivityStatus;
  metadata?: Record<string, unknown>;
  relatedResourceId?: string | null;
};

export function filterActivitiesByQueryAndCategory(items: ActivityItem[], query: string, category: ActivityCategory) {
  const normalizedQuery = query.trim().toLowerCase();
  return items.filter((item) => {
    const matchesCategory = category === "all" || item.category === category;
    if (!matchesCategory) return false;
    if (!normalizedQuery) return true;

    const haystack = [
      item.title,
      item.description,
      item.metadata?.fileName,
      item.metadata?.conversationName,
      item.metadata?.resourceName,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    return haystack.includes(normalizedQuery);
  });
}

export function getPeriodLabel(timestamp: Date, now: Date) {
  const diffDays = Math.floor((now.setHours(0, 0, 0, 0) - timestamp.setHours(0, 0, 0, 0)) / 86400000);

  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays <= 7) return "Earlier This Week";
  if (diffDays <= 14) return "Last Week";
  return "Older";
}

export function getStatusBadge(status: ActivityStatus) {
  switch (status) {
    case "running":
      return { label: "Running", className: "bg-sky-50 text-sky-700" };
    case "failed":
      return { label: "Failed", className: "bg-rose-50 text-rose-700" };
    case "cancelled":
      return { label: "Cancelled", className: "bg-stone-100 text-stone-700" };
    default:
      return { label: "Completed", className: "bg-emerald-50 text-emerald-700" };
  }
}

export function getActivityCategoryLabel(category: ActivityCategory | string) {
  switch (category) {
    case "files":
      return "Files";
    case "ai":
      return "AI";
    case "conversations":
      return "Conversations";
    case "search":
      return "Search";
    case "connected-apps":
      return "Connected Apps";
    case "system":
      return "System";
    default:
      return "All";
  }
}

export function getActivityIcon(type: string) {
  switch (type) {
    case "file_uploaded":
    case "file_deleted":
    case "file_renamed":
    case "file_summarized":
    case "file_explained":
    case "ai_extracted_information":
      return "📄";
    case "asked_synzept":
    case "ai_response_completed":
    case "ai_generated_summary":
    case "ai_generated_report":
    case "ai_generated_workflow":
      return "🤖";
    case "semantic_search":
    case "file_search":
    case "workspace_search":
      return "🔎";
    case "new_conversation":
    case "continued_conversation":
    case "conversation_renamed":
      return "💬";
    case "gmail_synced":
    case "calendar_synced":
    case "drive_synced":
      return "🔗";
    default:
      return "⚙️";
  }
}

export function getActivityTitle(type: string, fallback: string) {
  const mappings: Record<string, string> = {
    file_uploaded: "File uploaded",
    file_deleted: "File deleted",
    file_renamed: "File renamed",
    file_summarized: "File summarized",
    file_explained: "File explained",
    ai_extracted_information: "AI extracted information",
    asked_synzept: "Asked Synzept",
    ai_response_completed: "AI response completed",
    ai_generated_summary: "AI generated summary",
    ai_generated_report: "AI generated report",
    ai_generated_workflow: "AI generated workflow",
    semantic_search: "Semantic search",
    file_search: "File search",
    workspace_search: "Workspace search",
    new_conversation: "New conversation",
    continued_conversation: "Continued conversation",
    conversation_renamed: "Conversation renamed",
    gmail_synced: "Gmail synced",
    calendar_synced: "Calendar synced",
    drive_synced: "Drive synced",
    logged_in: "Logged in",
    logged_out: "Logged out",
    settings_changed: "Settings changed",
    profile_updated: "Profile updated",
    subscription_changed: "Subscription changed",
  };

  return mappings[type] || fallback;
}
