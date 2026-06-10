import { useState, useEffect } from "react";
import { useLocation, Link, Navigate } from "react-router-dom";
import { savePrediction, checkPredictionExists } from "@/services/api";
import { ShieldCheck, Crosshair } from "lucide-react";
import { marked } from "marked";
import { toast } from "sonner";
import { horizons, CONFIDENCE_BADGE, RESULT_CACHE_KEY, type PredResult } from "./search/shared";

marked.setOptions({ breaks: true, gfm: true });

const SearchResult = () => {
  const location = useLocation();

  // 优先从 location.state 获取，其次从 sessionStorage 获取
  let initial: PredResult | null = (location.state as PredResult) || null;
  if (!initial?.predContent) {
    try {
      const cached = sessionStorage.getItem(RESULT_CACHE_KEY);
      if (cached) initial = JSON.parse(cached) as PredResult;
    } catch { /* ignore */ }
  }

  const [result] = useState<PredResult | null>(initial);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(true);

  // 页面加载时检查是否已存在该预测记录
  useEffect(() => {
    if (!result?.predContent) return;
    const horizon = result.classifyType === "industry" ? "short_long" : result.selectedHorizon;
    checkPredictionExists(result.classifyType, result.classifyName, result.classifyName, horizon)
      .then((res) => {
        if (res.data.data?.exists) setSaved(true);
      })
      .catch(() => { /* ignore */ })
      .finally(() => setChecking(false));
  }, []);

  // 数据缺失则重定向
  if (!result?.predContent) {
    return <Navigate to="/" replace />;
  }

  const {
    classifyType,
    classifyName,
    selectedHorizon,
    predContent,
    predConfidence,
    predDataSnapshot,
  } = result;

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
      <h1 className="text-[32px] font-medium text-black">VATES</h1>

      <div className="w-full max-w-[50%] mt-8 space-y-5">
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
          <Link to="/" className="text-xs text-gray-400 hover:text-gray-600 transition-colors">重新搜索</Link>
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
            disabled={saved || saving || checking}
            onClick={handleSave}
          >
            <Crosshair className="h-4 w-4 mr-1.5" />
            {saved ? "已开启跟踪" : saving ? "保存中..." : checking ? "检查中..." : "保存预测记录并开启跟踪"}
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
    </div>
  );
};

export default SearchResult;
