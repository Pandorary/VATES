import { useState, useEffect } from "react";
import { getPredictionRecords, getPredictionDetail, deletePrediction, triggerReview } from "@/services/api";
import { Button } from "@/components/ui/button";
import {
  Crosshair,
  ChevronDown,
  ChevronUp,
  X,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Database,
  FileText,
  Trash2,
} from "lucide-react";
import { marked } from "marked";
import { toast } from "sonner";

marked.setOptions({ breaks: true, gfm: true });

const STATUS_MAP: Record<string, { label: string; bg: string; text: string }> = {
  tracking: { label: "跟踪中", bg: "bg-blue-50", text: "text-blue-600" },
  reviewed_match: { label: "已复盘-符合", bg: "bg-emerald-50", text: "text-emerald-600" },
  reviewed_deviate: { label: "已复盘-偏离", bg: "bg-amber-50", text: "text-amber-600" },
  expired: { label: "已失效", bg: "bg-gray-50", text: "text-gray-500" },
};

const HORIZON_MAP: Record<string, string> = {
  tomorrow: "下一交易日",
  week: "未来5个交易日",
  "1m": "未来1个月",
  "3m": "未来3个月",
  short_long: "短期+长期",
};

const CONFIDENCE_MAP: Record<string, { bg: string; text: string }> = {
  "高": { bg: "bg-emerald-50", text: "text-emerald-600" },
  "中": { bg: "bg-amber-50", text: "text-amber-600" },
  "低": { bg: "bg-red-50", text: "text-red-600" },
};

interface PredictionRecord {
  id: string;
  type: string;
  code: string;
  name: string;
  horizon: string;
  prediction_content: string;
  confidence_label: string;
  status: string;
  created_at: string | null;
}

interface PredictionDetail {
  id: string;
  type: string;
  code: string;
  name: string;
  horizon: string;
  prediction_content: string;
  confidence_label: string;
  status: string;
  created_at: string | null;
  data_snapshot: any;
  reviews: ReviewRecord[];
}

interface ReviewRecord {
  id: string;
  review_type: string;
  accuracy_rating: string;
  deviation_reason: string;
  review_content: string;
  created_at: string | null;
}

const PredictionTrack = () => {
  const [tab, setTab] = useState<"stock" | "industry">("stock");
  const [items, setItems] = useState<PredictionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<PredictionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reviewing, setReviewing] = useState<string | null>(null);

  useEffect(() => {
    fetchRecords();
  }, [tab]);

  async function fetchRecords() {
    setLoading(true);
    try {
      const res = await getPredictionRecords(tab);
      setItems(res.data.data || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  async function toggleExpand(id: string) {
    if (expanded === id) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(id);
    setDetailLoading(true);
    try {
      const res = await getPredictionDetail(id);
      setDetail(res.data.data);
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleReview(id: string) {
    setReviewing(id);
    try {
      const res = await triggerReview(id);
      if (res.data.code === 400) {
        toast.error(res.data.message);
        return;
      }
      toast.success("复盘已生成");
      // Refresh detail
      if (expanded === id) {
        const detailRes = await getPredictionDetail(id);
        setDetail(detailRes.data.data);
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.message || "复盘失败");
    } finally {
      setReviewing(null);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deletePrediction(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
      if (expanded === id) {
        setExpanded(null);
        setDetail(null);
      }
      toast.success("已删除");
    } catch {
      toast.error("删除失败");
    }
  }

  const stockCount = items.filter((i) => i.type === "stock").length;
  const industryCount = items.filter((i) => i.type === "industry").length;

  return (
    <div className="min-h-[calc(100vh-56px)] p-8">
      <div className="max-w-[860px] mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-semibold text-foreground tracking-tight">预测记录</h2>
            <p className="text-sm text-muted-foreground mt-1">查看和管理已保存的预测记录与复盘报告</p>
          </div>
        </div>

        {/* Tab 切换 */}
        <div className="flex gap-2 mb-6">
          <button
            className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
              tab === "stock"
                ? "border-primary/40 bg-primary/5 text-primary"
                : "border-border/30 text-muted-foreground hover:bg-muted/30"
            }`}
            onClick={() => setTab("stock")}
          >
            个股预测 {stockCount > 0 && <span className="text-xs opacity-60">({stockCount}/10)</span>}
          </button>
          <button
            className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
              tab === "industry"
                ? "border-primary/40 bg-primary/5 text-primary"
                : "border-border/30 text-muted-foreground hover:bg-muted/30"
            }`}
            onClick={() => setTab("industry")}
          >
            行业预测 {industryCount > 0 && <span className="text-xs opacity-60">({industryCount}/3)</span>}
          </button>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mr-2" />
            <span className="text-sm text-muted-foreground">加载中...</span>
          </div>
        )}

        {!loading && items.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            <Crosshair className="h-12 w-12 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              暂无{tab === "stock" ? "个股" : "行业"}预测记录，请在 AI 预测页面生成并保存预测
            </p>
          </div>
        )}

        {!loading && items.length > 0 && (
          <div className="flex flex-col gap-4">
            {items.map((item) => {
              const statusInfo = STATUS_MAP[item.status] || STATUS_MAP.tracking;
              const confInfo = CONFIDENCE_MAP[item.confidence_label] || CONFIDENCE_MAP["中"];
              const isExpanded = expanded === item.id;

              return (
                <div key={item.id} className="bg-card rounded-lg border overflow-hidden">
                  <div className="flex items-center justify-between px-6 py-4">
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-medium text-foreground">{item.name}</h3>
                      <span className={`text-[11px] px-2 py-0.5 rounded-md font-medium ${statusInfo.bg} ${statusInfo.text}`}>
                        {statusInfo.label}
                      </span>
                      <span className={`text-[11px] px-2 py-0.5 rounded-md font-medium ${confInfo.bg} ${confInfo.text}`}>
                        置信度:{item.confidence_label || "中"}
                      </span>
                      {item.horizon && (
                        <span className="text-xs text-muted-foreground">
                          {HORIZON_MAP[item.horizon] || item.horizon}
                        </span>
                      )}
                      <span className="text-xs text-muted-foreground/50">
                        {item.created_at?.slice(0, 10)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-xs rounded-lg"
                        disabled={reviewing === item.id}
                        onClick={() => handleReview(item.id)}
                      >
                        <RefreshCw className={`h-3 w-3 mr-1 ${reviewing === item.id ? "animate-spin" : ""}`} />
                        触发复盘
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => toggleExpand(item.id)}>
                        {isExpanded ? <ChevronUp className="h-4 w-4 mr-1" /> : <ChevronDown className="h-4 w-4 mr-1" />}
                        {isExpanded ? "收起" : "详情"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-500 hover:text-red-600 hover:bg-red-50"
                        onClick={() => handleDelete(item.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="border-t px-6 py-4">
                      {detailLoading && (
                        <div className="flex items-center justify-center py-8">
                          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mr-2" />
                          <span className="text-sm text-muted-foreground">加载详情...</span>
                        </div>
                      )}

                      {!detailLoading && detail && (
                        <div className="space-y-4">
                          {/* 预测报告 */}
                          <div>
                            <h4 className="text-sm font-medium text-foreground mb-2 flex items-center gap-1.5">
                              <FileText className="h-3.5 w-3.5" />
                              原始预测报告
                            </h4>
                            <div
                              className="prose prose-sm max-w-none prose-p:text-foreground/75 prose-headings:text-foreground/90 prose-strong:text-foreground/85 prose-li:text-foreground/75 [&_h3]:text-sm [&_h3]:font-medium [&_p]:my-1.5 [&_p]:leading-relaxed [&_li]:my-0.5"
                              dangerouslySetInnerHTML={{ __html: marked.parse(detail.prediction_content) as string }}
                            />
                          </div>

                          {/* 数据快照 */}
                          {detail.data_snapshot && (
                            <div>
                              <h4 className="text-sm font-medium text-foreground mb-2 flex items-center gap-1.5">
                                <Database className="h-3.5 w-3.5" />
                                数据快照
                              </h4>
                              <pre className="text-xs text-muted-foreground bg-muted/30 p-3 rounded-lg overflow-x-auto max-h-48">
                                {JSON.stringify(detail.data_snapshot, null, 2)}
                              </pre>
                            </div>
                          )}

                          {/* 复盘记录 */}
                          {detail.reviews && detail.reviews.length > 0 && (
                            <div>
                              <h4 className="text-sm font-medium text-foreground mb-2 flex items-center gap-1.5">
                                <ShieldCheck className="h-3.5 w-3.5" />
                                复盘记录 ({detail.reviews.length})
                              </h4>
                              <div className="space-y-3">
                                {detail.reviews.map((review) => (
                                  <div key={review.id} className="border rounded-lg p-4">
                                    <div className="flex items-center gap-2 mb-2">
                                      <span className="text-xs text-muted-foreground">{review.review_type}</span>
                                      <span className="text-xs text-muted-foreground/50">{review.created_at?.slice(0, 10)}</span>
                                    </div>
                                    <div
                                      className="prose prose-sm max-w-none prose-p:text-foreground/75 prose-headings:text-foreground/90 [&_p]:my-1 [&_p]:leading-relaxed"
                                      dangerouslySetInnerHTML={{ __html: marked.parse(review.review_content) as string }}
                                    />
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {(!detail.reviews || detail.reviews.length === 0) && (
                            <p className="text-xs text-muted-foreground py-2">暂无复盘记录，点击「触发复盘」手动生成</p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 免责声明 */}
        <div className="border-t border-border/40 pt-4 mt-8">
          <p className="text-xs text-muted-foreground/60 leading-relaxed">
            本内容由AI生成，仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。
          </p>
        </div>
      </div>
    </div>
  );
};

export default PredictionTrack;
