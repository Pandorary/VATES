import { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { searchClassify, getStockBrief } from "@/services/api";
import { Loader2, ShieldCheck } from "lucide-react";
import { marked } from "marked";
import { horizons, CONFIDENCE_BADGE } from "./search/shared";

marked.setOptions({ breaks: true, gfm: true });

const SearchClassified = () => {
  const [searchParams] = useSearchParams();
  const q = searchParams.get("q") || "";
  const typeParam = searchParams.get("type") as "stock" | "industry" | "";
  const nameParam = searchParams.get("name") || "";

  const [classifyType, setClassifyType] = useState<"stock" | "industry" | "">(typeParam);
  const [classifyName, setClassifyName] = useState(nameParam);
  const [classifyCode, setClassifyCode] = useState("");
  const [loading, setLoading] = useState(!typeParam);
  const [error, setError] = useState("");

  // 简要分析
  const [briefLoading, setBriefLoading] = useState(false);
  const [briefContent, setBriefContent] = useState("");
  const [briefConfidence, setBriefConfidence] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    if (typeParam && nameParam) return;

    // 直接访问该页面，需要调用 API
    if (!q) {
      navigate("/", { replace: true });
      return;
    }

    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const res = await searchClassify(q);
        const data = res.data.data;
        if (cancelled) return;
        if (data.type === "stock" || data.type === "industry") {
          setClassifyType(data.type);
          setClassifyName(data.name);
          if (data.code) setClassifyCode(data.code);
        } else {
          setError("未查询到相关标的信息，请核对名称或代码");
        }
      } catch {
        setError("请求失败，请确认后端服务已启动");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [q, typeParam, nameParam, navigate]);

  // 个股：获取简要分析
  useEffect(() => {
    if (classifyType !== "stock" || !classifyName) return;

    let cancelled = false;
    (async () => {
      setBriefLoading(true);
      try {
        const code = classifyCode || classifyName;
        const res = await getStockBrief(code, classifyName);
        const data = res.data.data;
        if (cancelled) return;
        setBriefContent(data.content || "");
        setBriefConfidence(data.confidence || "");
      } catch {
        if (!cancelled) setBriefConfidence("");
      } finally {
        if (!cancelled) setBriefLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [classifyType, classifyName]);

  // 行业：自动跳转预测
  useEffect(() => {
    if (classifyType === "industry" && classifyName) {
      const timer = setTimeout(() => {
        navigate(`/predicting?type=industry&name=${encodeURIComponent(classifyName)}`);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [classifyType, classifyName, navigate]);

  function selectHorizon(key: string) {
    navigate(`/predicting?type=stock&name=${encodeURIComponent(classifyName)}&horizon=${key}`);
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-5 pt-28 pb-20 px-4">
        <Loader2 className="h-5 w-5 animate-spin text-primary" />
        <p className="text-sm text-gray-400">AI 正在识别...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-5 pt-28 pb-20 px-4">
        <p className="text-sm text-gray-400">{error}</p>
        <Link to="/" className="text-sm text-primary hover:underline">返回首页重新搜索</Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center gap-5 pt-28 pb-20 px-4">
      {/* 标题 */}
      <div className="flex items-center gap-2 mb-1">
        <h1 className="text-[32px] font-medium text-black">VATES</h1>
      </div>

      {/* 分类结果 */}
      <div className="w-[460px] max-w-[90vw] mt-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="text-base font-medium text-gray-900">{classifyName}</span>
            <span className={`text-[11px] px-2 py-0.5 rounded-md font-medium ${classifyType === "stock" ? "bg-blue-50 text-blue-600" : "bg-emerald-50 text-emerald-600"}`}>
              {classifyType === "stock" ? "个股" : "行业"}
            </span>
          </div>
          <Link to="/" className="text-xs text-gray-400 hover:text-gray-600 transition-colors">重新搜索</Link>
        </div>

        {classifyType === "stock" && (
          <>
            {/* 简要分析 */}
            {briefLoading && (
              <div className="mb-4 flex items-center gap-2 text-sm text-gray-400">
                <Loader2 className="h-4 w-4 animate-spin" />
                正在调取数据，AI 分析中...
              </div>
            )}
            {briefContent && (
              <div className="mb-5 bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-sm font-medium text-gray-800">AI 简要分析</span>
                  {briefConfidence && (
                    <span className={`inline-flex items-center gap-1 text-[11px] font-medium rounded px-2 py-0.5 ${(CONFIDENCE_BADGE[briefConfidence] || CONFIDENCE_BADGE["中"]).bg} ${(CONFIDENCE_BADGE[briefConfidence] || CONFIDENCE_BADGE["中"]).text}`}>
                      <ShieldCheck className="h-3 w-3" />
                      数据置信度：{briefConfidence}
                    </span>
                  )}
                </div>
                <div
                  className="prose prose-sm max-w-none prose-p:text-gray-600 prose-headings:text-gray-800 prose-strong:text-gray-700 prose-li:text-gray-600 [&_h3]:text-sm [&_h3]:font-medium [&_h3]:mt-2 [&_h3]:mb-1 [&_p]:my-1 [&_p]:leading-relaxed [&_ul]:my-1.5 [&_li]:my-0.5"
                  dangerouslySetInnerHTML={{ __html: marked.parse(briefContent) as string }}
                />
              </div>
            )}
            <p className="text-sm text-gray-400 mb-4">选择预测时段进行 AI 深度推演</p>
            <div className="grid grid-cols-4 gap-3">
              {horizons.map((h) => {
                const Icon = h.icon;
                return (
                  <button
                    key={h.key}
                    className="flex flex-col items-center gap-2 py-4 px-2 rounded-xl border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-900 hover:border-gray-300 transition-colors"
                    onClick={() => selectHorizon(h.key)}
                  >
                    <Icon className="h-5 w-5" />
                    <span className="text-xs font-medium">{h.label}</span>
                  </button>
                );
              })}
            </div>
          </>
        )}

        {classifyType === "industry" && (
          <p className="text-sm text-gray-400">正在跳转行业研判...</p>
        )}
      </div>
    </div>
  );
};

export default SearchClassified;
