// API 统一响应
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

// 分页
export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// 市场状态
export type MarketStatus = 'ICE' | 'WARM' | 'HIGH' | 'RETREAT'

export interface MarketTemperature {
  trade_date: string
  status: MarketStatus
  status_text: string
  advice: string
  details: {
    max_board_height: number
    promotion_rate: number
    bomb_rate: number
    yesterday_avg_return: number
  }
  main_flows: SectorFlow[]
}

export interface SectorFlow {
  sector: string
  net_inflow: number
  lead_stock: string
}

// 股票
export interface StockSearchResult {
  code: string
  name: string
  industry: string
  close: number
  change_pct: number
}

export interface StockDetail {
  code: string
  name: string
  industry: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
  change_pct: number
  turnover_rate: number
  sector_strength: number
}

// 模式
export interface PatternSignal {
  pattern_id: number
  name: string
  description: string
  details: Record<string, unknown>
  confirm_condition: string
  fail_condition: string
  risk_reference: number | null
  history_stats?: PatternHistoryStats
}

export interface PatternHistoryStats {
  win_rate: number
  avg_pnl_ratio: number
  sample_count: number
}

// 用户
export interface WatchlistItem {
  code: string
  name: string
  close: number
  change_pct: number
  matched_pattern: string | null
  in_observe_pool: boolean
}

// 复盘
export interface ReviewReport {
  trade_date: string
  market_status: MarketStatus
  status_text: string
  max_board_height: number
  promotion_rate: number
  bomb_rate: number
  yesterday_avg_return: number
  main_flows: SectorFlow[]
  signals: PatternSignal[]
  risk_alerts: string[]
}
