import type { LucideIcon } from "lucide-react";
import { Clock, CalendarDays, CalendarRange, Telescope } from "lucide-react";

export interface Horizon {
  key: string;
  label: string;
  icon: LucideIcon;
}

export const horizons: Horizon[] = [
  { key: "tomorrow", label: "下一交易日", icon: Clock },
  { key: "week", label: "未来5个交易日", icon: CalendarDays },
  { key: "1m", label: "未来1个月", icon: CalendarRange },
  { key: "3m", label: "未来3个月", icon: Telescope },
];

export const CONFIDENCE_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  "高": { bg: "bg-emerald-50", text: "text-emerald-600", label: "数据置信度：高" },
  "中": { bg: "bg-amber-50", text: "text-amber-600", label: "数据置信度：中" },
  "低": { bg: "bg-red-50", text: "text-red-600", label: "数据置信度：低" },
};

export const HISTORY_KEY = "vates_search_history";
export const HISTORY_MAX = 10;

export function loadHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveHistory(items: string[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items));
}

export function appendHistory(query: string): string[] {
  const trimmed = query.trim();
  if (!trimmed) return loadHistory();
  const list = loadHistory().filter((q) => q !== trimmed);
  list.unshift(trimmed);
  const next = list.slice(0, HISTORY_MAX);
  saveHistory(next);
  return next;
}

export const RESULT_CACHE_KEY = "vates_pred_result";

export interface PredResult {
  classifyType: "stock" | "industry";
  classifyName: string;
  selectedHorizon: string;
  predContent: string;
  predConfidence: string;
  predDataSnapshot: any;
}
