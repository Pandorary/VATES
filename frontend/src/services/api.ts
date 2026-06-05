import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  timeout: 120000,
});

// 搜索分类
export function searchClassify(query: string) {
  return api.post("/search", { query });
}

// 个股简要分析
export function getStockBrief(code: string, name?: string) {
  return api.get("/stock/" + encodeURIComponent(code) + "/brief", { params: name ? { name } : {} });
}

// ---------- 预测 ----------

export function predictStock(code: string, horizon: string) {
  return api.post("/prediction/stock", { code, horizon });
}

export function predictIndustry(name: string) {
  return api.post("/prediction/industry", { name });
}

export function savePrediction(data: {
  type: string;
  code: string;
  name: string;
  horizon: string;
  content: string;
  confidence: string;
  data_snapshot: any;
  source_urls: string[];
}) {
  // prediction_id 由后端生成，这里传整个数据对象
  return api.post(`/prediction/save`, data);
}

export function getPredictionRecords(type?: string) {
  return api.get("/prediction/records", { params: type ? { type } : {} });
}

export function getPredictionDetail(id: string) {
  return api.get(`/prediction/records/${id}`);
}

export function deletePrediction(id: string) {
  return api.delete(`/prediction/records/${id}`);
}

export function triggerReview(id: string) {
  return api.post(`/prediction/records/${id}/review`);
}

// ---------- Prompt 模板 CRUD ----------

export interface PromptTemplate {
  id: string;
  scene: string;
  role: string;
  role_name: string;
  module: string;
  skill: string;
  skill_summary: string;
  skill_detail: string;
  is_active: boolean;
  created_at: string | null;
  created_by: string;
  updated_at: string | null;
  updated_by: string;
}

export interface PromptListParams {
  page?: number;
  page_size?: number;
  scene?: string;
  role?: string;
  module?: string;
  search?: string;
}

export function getPromptTemplates(params?: PromptListParams) {
  return api.get("/admin/prompt-templates", { params });
}

export function getPromptTemplate(id: string) {
  return api.get(`/admin/prompt-templates/${id}`);
}

export function createPromptTemplate(data: {
  scene: string;
  role: string;
  role_name: string;
  module: string;
  skill: string;
  skill_summary: string;
  skill_detail: string;
}) {
  return api.post("/admin/prompt-templates", data);
}

export function updatePromptTemplate(
  id: string,
  data: {
    scene?: string;
    role?: string;
    role_name?: string;
    module?: string;
    skill?: string;
    skill_summary?: string;
    skill_detail?: string;
    is_active?: boolean;
  },
) {
  return api.put(`/admin/prompt-templates/${id}`, data);
}

export function deletePromptTemplate(id: string) {
  return api.delete(`/admin/prompt-templates/${id}`);
}

export function copyPromptTemplate(id: string) {
  return api.post(`/admin/prompt-templates/${id}/copy`);
}

// ---------- 持仓 ----------

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

export function getHoldings() {
  return api.get("/holdings");
}

export function createHolding(data: {
  code: string;
  cost_price: number;
  shares: number;
  total_assets: number;
}) {
  return api.post("/holdings", data);
}

export function updateHolding(id: number, data: { cost_price?: number; shares?: number }) {
  return api.put(`/holdings/${id}`, data);
}

export function deleteHolding(id: number) {
  return api.delete(`/holdings/${id}`);
}

export function diagnoseHolding(id: number) {
  return api.post(`/holdings/${id}/diagnose`);
}

export function reviewHolding(id: number) {
  return api.post(`/holdings/${id}/review`);
}

export function refreshHoldingPrice(id: number) {
  return api.post(`/holdings/${id}/refresh`);
}

export function getTotalAssets() {
  return api.get("/holdings/total-assets");
}

export function updateTotalAssets(value: number) {
  return api.put("/holdings/total-assets", { value });
}

// ---------- 预测跟踪（旧版兼容） ----------

export function getTrackingList() {
  return api.get("/tracking");
}

export function addTracking(type: string, name: string) {
  return api.post("/tracking", { type, name });
}

export function deleteTracking(id: number) {
  return api.delete(`/tracking/${id}`);
}

export function latestPrediction(id: number) {
  return api.get(`/tracking/${id}/latest-prediction`);
}

export function deviationAnalysis(name: string, type: string) {
  return api.post("/tracking/deviation-analysis", { name, type });
}

export default api;
