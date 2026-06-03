import { useState } from "react";
import { searchClassify, predictStock, predictIndustry, savePrediction } from "@/services/api";
import { Search, Sparkles, Loader2, ShieldCheck, Clock, CalendarDays, CalendarRange, Telescope, Crosshair } from "lucide-react";
import { marked } from "marked";
import { toast } from "sonner";
import type { LucideIcon } from "lucide-react";

marked.setOptions({ breaks: true, gfm: true });

interface Horizon {
  key: string;
  label: string;
  icon: LucideIcon;
}

const horizons: Horizon[] = [
  { key: "tomorrow", label: "下一交易日", icon: Clock },
  { key: "week", label: "未来5个交易日", icon: CalendarDays },
  { key: "1m", label: "未来1个月", icon: CalendarRange },
  { key: "3m", label: "未来3个月", icon: Telescope },
];

const CONFIDENCE_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  "高": { bg: "bg-emerald-50", text: "text-emerald-600", label: "数据置信度：高" },
  "中": { bg: "bg-amber-50", text: "text-amber-600", label: "数据置信度：中" },
  "低": { bg: "bg-red-50", text: "text-red-600", label: "数据置信度：低" },
};

type Step = "search" | "classified" | "predicting" | "result";

const Home = () => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [classifyType, setClassifyType] = useState<"stock" | "industry" | "unknown" | "">("");
  const [classifyName, setClassifyName] = useState("");

  const [selectedHorizon, setSelectedHorizon] = useState("");
  const [predContent, setPredContent] = useState("");
  const [predConfidence, setPredConfidence] = useState("");
  const [predDataSnapshot, setPredDataSnapshot] = useState<any>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  const [step, setStep] = useState<Step>("search");

  function reset() {
    setQuery("");
    setClassifyType("");
    setClassifyName("");
    setSelectedHorizon("");
    setPredContent("");
    setPredConfidence("");
    setPredDataSnapshot(null);
    setSaved(false);
    setSaving(false);
    setError("");
    setStep("search");
  }

  async function handleSearch() {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError("");
    try {
      const res = await searchClassify(q);
      const data = res.data.data;
      if (data.type === "stock") {
        setClassifyType("stock");
        setClassifyName(data.name);
        setStep("classified");
      } else if (data.type === "industry") {
        setClassifyType("industry");
        setClassifyName(data.name);
        setStep("classified");
        triggerIndustryPrediction(data.name);
      } else {
        setError("未查询到相关标的信息，请核对名称或代码");
      }
    } catch {
      setError("请求失败，请确认后端服务已启动");
    } finally {
      setLoading(false);
    }
  }

  async function selectStockHorizon(key: string) {
    setSelectedHorizon(key);
    setStep("predicting");
    setPredContent("");
    setPredConfidence("");
    setPredDataSnapshot(null);
    setSaved(false);
    try {
      const res = await predictStock(classifyName, key);
      const data = res.data.data;
      if (res.data.code !== 200 && res.data.code !== 0) {
        setError(res.data.message || "预测失败");
        setStep("classified");
        return;
      }
      setPredContent(data.content || "");
      setPredConfidence(data.confidence || "");
      setPredDataSnapshot(data.data_snapshot || null);
      setStep("result");
    } catch (e: any) {
      setError(e?.response?.data?.message || "预测请求失败");
      setStep("classified");
    }
  }

  async function triggerIndustryPrediction(name?: string) {
    const targetName = name || classifyName;
    setStep("predicting");
    setPredContent("");
    setPredConfidence("");
    setPredDataSnapshot(null);
    setSaved(false);
    try {
      const res = await predictIndustry(targetName);
      const data = res.data.data;
      if (res.data.code !== 200 && res.data.code !== 0) {
        setError(res.data.message || "预测失败");
        setStep("classified");
        return;
      }
      setPredContent(data.content || "");
      setPredConfidence(data.confidence || "");
      setPredDataSnapshot(data.data_snapshot || null);
      setStep("result");
    } catch (e: any) {
      setError(e?.response?.data?.message || "行业预测请求失败");
      setStep("classified");
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      const res = await savePrediction({
        type: classifyType,
        code: classifyName,
        name: classifyName,
        horizon: classifyType === "industry" ? "short_long" : selectedHorizon,
        content: predContent,
        confidence: predConfidence,
        data_snapshot: predDataSnapshot,
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

  const badge = CONFIDENCE_BADGE[predConfidence] || CONFIDENCE_BADGE["中"];

  return (
    <div className="flex flex-col items-center justify-center gap-5 pt-28 pb-20 px-4">
      {/* 标题 */}
      <div className="flex items-center gap-2 mb-1">
        <h1 className="text-[32px] font-medium text-black">VATES</h1>
      </div>

      {/* 搜索框 */}
      <div className="w-[460px] max-w-[90vw] relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 h-4 w-4" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="搜索股票代码或名称"
          className="flex h-11 w-full rounded-xl border border-gray-300 bg-white pl-10 pr-4 text-[15px] text-gray-900 placeholder:text-gray-400 outline-none transition-all focus:ring-2 focus:ring-primary/20 focus:border-primary"
          disabled={loading}
        />
      </div>

      {/* 搜索状态 */}
      {loading && step === "search" && (
        <p className="text-sm text-gray-400 mt-1">AI 正在识别...</p>
      )}
      {error && step === "search" && (
        <p className="text-sm text-gray-400 mt-1">{error}</p>
      )}

      {/* 个股时段选择 */}
      {step === "classified" && classifyType === "stock" && (
        <div className="w-[460px] max-w-[90vw] mt-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="text-base font-medium text-gray-900">{classifyName}</span>
              <span className="text-[11px] px-2 py-0.5 rounded-md font-medium bg-blue-50 text-blue-600">个股</span>
            </div>
            <button onClick={reset} className="text-xs text-gray-400 hover:text-gray-600 transition-colors">重新搜索</button>
          </div>
          <p className="text-sm text-gray-400 mb-4">选择预测时段进行 AI 推演</p>
          <div className="grid grid-cols-4 gap-3">
            {horizons.map((h) => {
              const Icon = h.icon;
              return (
                <button
                  key={h.key}
                  className="flex flex-col items-center gap-2 py-4 px-2 rounded-xl border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-900 hover:border-gray-300 transition-colors"
                  onClick={() => selectStockHorizon(h.key)}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-xs font-medium">{h.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* 预测进行中 */}
      {step === "predicting" && (
        <div className="flex items-center gap-3 mt-10">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-gray-400">数据引擎获取中，AI 推演中...</span>
        </div>
      )}

      {/* 预测结果 */}
      {step === "result" && predContent && (
        <div className="w-[680px] max-w-[90vw] mt-8 space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold text-gray-900">{classifyName}</span>
              <span className={`text-[11px] px-2 py-0.5 rounded-md font-medium ${classifyType === "stock" ? "bg-blue-50 text-blue-600" : "bg-emerald-50 text-emerald-600"}`}>
                {classifyType === "stock" ? "个股预测" : "行业研判"}
              </span>
              {selectedHorizon && classifyType === "stock" && (
                <span className="text-xs text-gray-400">
                  {horizons.find(h => h.key === selectedHorizon)?.label}
                </span>
              )}
            </div>
            <button onClick={reset} className="text-xs text-gray-400 hover:text-gray-600 transition-colors">重新搜索</button>
          </div>

          {/* 置信度 */}
          {predConfidence && (
            <div className="flex items-center gap-3">
              <span className={`inline-flex items-center gap-1.5 text-xs font-medium rounded-md px-3 py-1.5 ${badge.bg} ${badge.text}`}>
                <ShieldCheck className="h-3.5 w-3.5" />
                {badge.label}
              </span>
              {predConfidence === "中" && (
                <span className="text-xs text-amber-500">数据来源单一，请谨慎参考</span>
              )}
            </div>
          )}

          {/* 报告内容 */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div
              className="prose prose-sm max-w-none prose-p:text-gray-600 prose-headings:text-gray-800 prose-strong:text-gray-700 prose-li:text-gray-600 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-5 [&_h2]:mb-2 [&_h3]:text-sm [&_h3]:font-medium [&_h3]:mt-3 [&_h3]:mb-1.5 [&_p]:my-1.5 [&_p]:leading-relaxed [&_ul]:my-2 [&_li]:my-0.5"
              dangerouslySetInnerHTML={{ __html: marked.parse(predContent) as string }}
            />
          </div>

          {/* 保存按钮 */}
          <div className="flex items-center gap-3">
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

          {/* 免责声明 */}
          <div className="border-t border-gray-100 pt-4">
            <p className="text-xs text-gray-300 leading-relaxed">
              本内容由AI生成，仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;
