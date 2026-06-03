import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { predictStock, predictIndustry, savePrediction } from "@/services/api";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  Sparkles,
  Loader2,
  Clock,
  CalendarDays,
  CalendarRange,
  Telescope,
  ShieldCheck,
  Database,
  Scale,
  AlertOctagon,
  Crosshair,
  TrendingUp,
} from "lucide-react";
import { marked } from "marked";
import type { LucideIcon } from "lucide-react";
import { toast } from "sonner";

marked.setOptions({ breaks: true, gfm: true });

interface Horizon {
  key: string;
  label: string;
  icon: LucideIcon;
  bgClass: string;
  borderClass: string;
  textClass: string;
}

const horizons: Horizon[] = [
  { key: "tomorrow", label: "下一交易日", icon: Clock, bgClass: "bg-blue-50", borderClass: "border-blue-300/60", textClass: "text-blue-600" },
  { key: "week", label: "未来5个交易日", icon: CalendarDays, bgClass: "bg-emerald-50", borderClass: "border-emerald-300/60", textClass: "text-emerald-600" },
  { key: "1m", label: "未来1个月", icon: CalendarRange, bgClass: "bg-amber-50", borderClass: "border-amber-300/60", textClass: "text-amber-600" },
  { key: "3m", label: "未来3个月", icon: Telescope, bgClass: "bg-violet-50", borderClass: "border-violet-300/60", textClass: "text-violet-600" },
];

const MODULE_ICONS: Record<string, LucideIcon> = {
  "核心结论": TrendingUp,
  "数据依据": Database,
  "多空逻辑": Scale,
  "置信度评估": ShieldCheck,
  "失效条件": AlertOctagon,
};

const CONFIDENCE_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  "高": { bg: "bg-emerald-50", text: "text-emerald-600", label: "数据置信度：高" },
  "中": { bg: "bg-amber-50", text: "text-amber-600", label: "数据置信度：中" },
  "低": { bg: "bg-red-50", text: "text-red-600", label: "数据置信度：低" },
};

const AIPrediction = () => {
  const { stock: stockQuery = "" } = useParams();
  const navigate = useNavigate();
  const [active, setActive] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [content, setContent] = useState("");
  const [confidence, setConfidence] = useState("");
  const [dataSnapshot, setDataSnapshot] = useState<any>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isIndustry, setIsIndustry] = useState(false);
  const [industryLoading, setIndustryLoading] = useState(false);

  // 自动检测是否行业（简化逻辑：如果包含"行业/板块/概念"关键词则视为行业）
  function detectType(query: string): "stock" | "industry" {
    const keywords = ["行业", "板块", "概念", "赛道", "产业链"];
    return keywords.some(k => query.includes(k)) ? "industry" : "stock";
  }

  async function selectStockHorizon(key: string) {
    setActive(key);
    setLoading(true);
    setError("");
    setContent("");
    setConfidence("");
    setDataSnapshot(null);
    setSaved(false);
    try {
      const res = await predictStock(stockQuery, key);
      const data = res.data.data;
      if (res.data.code !== 200 && res.data.code !== 0) {
        setError(res.data.message || "预测失败");
        return;
      }
      setContent(data.content || "");
      setConfidence(data.confidence || "");
      setDataSnapshot(data.data_snapshot || null);
    } catch (e: any) {
      setError(e?.response?.data?.message || "预测请求失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  async function triggerIndustryPrediction() {
    setIndustryLoading(true);
    setLoading(true);
    setError("");
    setContent("");
    setConfidence("");
    setDataSnapshot(null);
    setSaved(false);
    setIsIndustry(true);
    try {
      const res = await predictIndustry(stockQuery);
      const data = res.data.data;
      if (res.data.code !== 200 && res.data.code !== 0) {
        setError(res.data.message || "预测失败");
        return;
      }
      setContent(data.content || "");
      setConfidence(data.confidence || "");
      setDataSnapshot(data.data_snapshot || null);
    } catch (e: any) {
      setError(e?.response?.data?.message || "行业预测请求失败");
    } finally {
      setLoading(false);
      setIndustryLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      const res = await savePrediction({
        type: isIndustry ? "industry" : "stock",
        code: stockQuery,
        name: stockQuery,
        horizon: isIndustry ? "short_long" : active,
        content,
        confidence,
        data_snapshot: dataSnapshot,
        source_urls: [],
      });
      if (res.data.code === 400) {
        toast.error(res.data.message);
        return;
      }
      setSaved(true);
      toast.success("已保存并开启跟踪");
    } catch (e: any) {
      toast.error(e?.response?.data?.message || "保存失败，请重试");
    } finally {
      setSaving(false);
    }
  }

  const queryType = detectType(stockQuery);
  const badge = CONFIDENCE_BADGE[confidence] || CONFIDENCE_BADGE["中"];

  return (
    <div className="min-h-[calc(100vh-56px)] p-8">
      <div className="max-w-[820px] mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-semibold text-foreground tracking-tight flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-primary" />
              AI 预测
            </h2>
            <p className="text-sm text-muted-foreground mt-1.5">
              {stockQuery} · {isIndustry ? "行业双时间维度研判" : "选择时段进行 AI 推演"}
            </p>
          </div>
          <Button variant="outline" size="sm" className="rounded-lg" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            返回
          </Button>
        </div>

        {/* 时段选择（仅个股） */}
        {queryType === "stock" && !isIndustry && (
          <div className="grid grid-cols-4 gap-3 mb-6">
            {horizons.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.key}
                  className={`flex flex-col items-center gap-2 py-4 px-3 rounded-lg border transition-colors ${
                    active === item.key
                      ? "border-primary/40 bg-primary/5 text-primary"
                      : "bg-card border-border/30 text-muted-foreground hover:bg-muted/30"
                  }`}
                  onClick={() => selectStockHorizon(item.key)}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-sm font-medium">{item.label}</span>
                </button>
              );
            })}
          </div>
        )}

        {/* 行业预测触发按钮 */}
        {queryType === "industry" && !content && !loading && (
          <div className="text-center py-10">
            <p className="text-sm text-muted-foreground mb-4">行业预测将生成包含短期（1-3个月）和长期（半年以上）的双时间维度研判报告</p>
            <Button onClick={triggerIndustryPrediction} className="rounded-lg">
              <Sparkles className="h-4 w-4 mr-1.5" />
              生成行业研判报告
            </Button>
          </div>
        )}

        {loading && (
          <div className="flex items-center gap-3 py-16 justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-sm text-muted-foreground">
              {industryLoading ? "AI 正在生成行业研判报告..." : "数据引擎获取中，AI 推演中..."}
            </span>
          </div>
        )}

        {error && (
          <div className="text-center py-16">
            <p className="text-sm text-muted-foreground">{error}</p>
          </div>
        )}

        {!loading && !error && content && (
          <div className="space-y-4">
            {/* 置信度徽章 */}
            {confidence && (
              <div className="flex items-center gap-3">
                <span className={`inline-flex items-center gap-1.5 text-xs font-medium rounded-md px-3 py-1.5 ${badge.bg} ${badge.text}`}>
                  <ShieldCheck className="h-3.5 w-3.5" />
                  {badge.label}
                </span>
                {confidence === "中" && (
                  <span className="text-xs text-amber-500">数据来源单一，请谨慎参考</span>
                )}
              </div>
            )}

            {/* 预测报告 */}
            <div className="bg-card rounded-lg border p-8">
              <div
                className="prose prose-sm max-w-none prose-p:text-foreground/75 prose-headings:text-foreground/90 prose-strong:text-foreground/85 prose-li:text-foreground/75 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mt-6 [&_h2]:mb-3 [&_h3]:text-base [&_h3]:font-medium [&_h3]:mt-4 [&_h3]:mb-2 [&_p]:my-2 [&_p]:leading-relaxed [&_ul]:my-2 [&_li]:my-1"
                dangerouslySetInnerHTML={{ __html: marked.parse(content) as string }}
              />
            </div>

            {/* 保存并开启跟踪 */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  className={`inline-flex items-center h-10 px-5 rounded-lg text-sm font-medium border transition-colors ${
                    saved
                      ? "border-emerald-300 bg-emerald-50 text-emerald-600"
                      : "border-primary/40 bg-primary/5 text-primary hover:bg-primary/10"
                  }`}
                  disabled={saved || saving}
                  onClick={handleSave}
                >
                  <Crosshair className="h-4 w-4 mr-1.5" />
                  {saved ? "已开启跟踪" : saving ? "保存中..." : "保存预测记录并开启跟踪"}
                </button>
                {saved && (
                  <a href="/prediction-track" className="text-xs text-primary hover:underline">查看跟踪记录 →</a>
                )}
              </div>
            </div>

            {/* 免责声明 */}
            <div className="border-t border-border/40 pt-4">
              <p className="text-xs text-muted-foreground/60 leading-relaxed">
                本内容由AI生成，仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。
              </p>
            </div>
          </div>
        )}

        {!loading && !error && !content && queryType === "stock" && (
          <div className="text-center py-16">
            <p className="text-sm text-muted-foreground">请选择上方时段开始预测</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIPrediction;
