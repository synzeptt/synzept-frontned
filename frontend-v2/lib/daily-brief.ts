import { request } from "@/lib/api";
import type { DailyBrief } from "../types/daily-brief";

export const dailyBriefApi = {
  today: () => request<DailyBrief>("/api/v2/daily-brief/today"),
  refresh: () => request<DailyBrief>("/api/v2/daily-brief/today/refresh", { method: "POST" }),
};
