// API 统一响应
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

// 分页
export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// 预测时段
export type StockHorizon = "tomorrow" | "week" | "1m" | "3m";

// 置信度标签
export type ConfidenceLabel = "高" | "中" | "低";

// 预测记录状态
export type PredictionStatus = "tracking" | "reviewed_match" | "reviewed_deviate" | "expired";

// 预测记录
export interface PredictionRecord {
  id: string;
  type: "stock" | "industry";
  code: string;
  name: string;
  horizon: string;
  prediction_content: string;
  confidence_label: ConfidenceLabel;
  status: PredictionStatus;
  created_at: string | null;
}

// 数据快照
export interface DataSnapshot {
  [key: string]: any;
  _source_urls?: string[];
  _fetch_timestamp?: string;
  _confidence?: ConfidenceLabel;
}

// 复盘记录
export interface ReviewRecord {
  id: string;
  prediction_id: string;
  review_type: string;
  accuracy_rating: string;
  deviation_reason: string;
  review_content: string;
  created_at: string | null;
}

// 预测详情
export interface PredictionDetail extends PredictionRecord {
  data_snapshot: DataSnapshot | null;
  reviews: ReviewRecord[];
}

// 持仓
export interface Holding {
  id: number;
  code: string;
  name: string;
  cost_price: number;
  shares: number;
  current_price: number | null;
  profit_amount: number | null;
  profit_pct: number | null;
  created_at: string | null;
  updated_at: string | null;
}

// 提示词业务场景
export interface PromptScene {
  code: string;
  label: string;
}
