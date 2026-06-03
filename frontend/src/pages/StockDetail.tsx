import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { sendChat, addTracking } from "@/services/api";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  ChevronDown,
  Building2,
  BarChart3,
  TrendingUp,
  DollarSign,
  AlertTriangle,
  FileText,
  Sparkles,
  Crosshair,
} from "lucide-react";
import { marked } from "marked";
import type { LucideIcon } from "lucide-react";

marked.setOptions({ breaks: true, gfm: true });

interface Section {
  key: string;
  title: string;
  icon: LucideIcon;
  bgClass: string;
  textClass: string;
  borderClass: string;
  collapsed: boolean;
  html: string;
}

const SECTION_CONFIG: Record<string, { title: string; icon: LucideIcon; bgClass: string; textClass: string; borderClass: string }> = {
  fundamentals: { title: "公司基本面", icon: Building2, bgClass: "bg-blue-50", textClass: "text-blue-600", borderClass: "border-blue-300/60" },
  financials: { title: "财报业绩", icon: BarChart3, bgClass: "bg-emerald-50", textClass: "text-emerald-600", borderClass: "border-emerald-300/60" },
  industry: { title: "行业趋势", icon: TrendingUp, bgClass: "bg-amber-50", textClass: "text-amber-600", borderClass: "border-amber-300/60" },
  valuation: { title: "估值弹性", icon: DollarSign, bgClass: "bg-violet-50", textClass: "text-violet-600", borderClass: "border-violet-300/60" },
  risks: { title: "风险", icon: AlertTriangle, bgClass: "bg-red-50", textClass: "text-red-600", borderClass: "border-red-300/60" },
  conclusion: { title: "投资结论", icon: FileText, bgClass: "bg-cyan-50", textClass: "text-cyan-600", borderClass: "border-cyan-300/60" },
};

function parseContent(raw: string): Section[] {
  const result: Section[] = [];
  try {
    let jsonStr = raw;
    const jsonMatch = raw.match(/```json\s*([\s\S]*?)\s*```/);
    if (jsonMatch) jsonStr = jsonMatch[1];
    else {
      const braceMatch = raw.match(/\{[\s\S]*\}/);
      if (braceMatch) jsonStr = braceMatch[0];
    }
    const data = JSON.parse(jsonStr);
    for (const [key, cfg] of Object.entries(SECTION_CONFIG)) {
      const markdown = (data as Record<string, string>)[key] || "";
      const html = marked.parse(markdown) as string;
      result.push({ key, title: cfg.title, icon: cfg.icon, bgClass: cfg.bgClass, textClass: cfg.textClass, borderClass: cfg.borderClass, collapsed: false, html });
    }
    return result;
  } catch {
    // fallback
  }

  const blocks = raw.split(/\n(?=## )/);
  for (const block of blocks) {
    const match = block.match(/^## (.+)/m);
    if (!match) continue;
    const blockTitle = match[1].trim();
    for (const [, cfg] of Object.entries(SECTION_CONFIG)) {
      if (blockTitle.includes(cfg.title) || cfg.title.includes(blockTitle)) {
        const html = marked.parse(block) as string;
        result.push({ key: cfg.title, title: cfg.title, icon: cfg.icon, bgClass: cfg.bgClass, textClass: cfg.textClass, borderClass: cfg.borderClass, collapsed: false, html });
        break;
      }
    }
  }

  if (!result.length) {
    result.push({
      key: "raw", title: "分析结果", icon: FileText, bgClass: "bg-gray-50", textClass: "text-gray-500", borderClass: "border-gray-300/60",
      collapsed: false, html: marked.parse(raw) as string,
    });
  }
  return result;
}

const StockDetail = () => {
  const { query: stockQuery = "" } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isCached, setIsCached] = useState(false);
  const [sections, setSections] = useState<Section[]>([]);
  const [trackState, setTrackState] = useState(0);
  const cycleRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const trackTextOffset = `${trackState * 1.25}rem`;
  const trackBtnClass =
    trackState === 1
      ? "border-amber-300 bg-amber-50 text-amber-600"
      : trackState >= 2
        ? "border-emerald-300 bg-emerald-50 text-emerald-600"
        : "border-border bg-background text-foreground hover:bg-muted/40";

  function stopTrackCycle() {
    if (cycleRef.current) {
      clearInterval(cycleRef.current);
      cycleRef.current = null;
    }
  }

  function startTrackCycle() {
    const endAt = Date.now() + 180000;
    const steps = [2, 3, 4];
    let idx = 0;
    setTrackState(steps[idx]);
    cycleRef.current = setInterval(() => {
      if (Date.now() >= endAt) {
        stopTrackCycle();
        setTrackState(4);
        return;
      }
      idx = (idx + 1) % steps.length;
      setTrackState(steps[idx]);
    }, 5000);
  }

  async function addToTracking() {
    if (trackState === 1) return;
    if (trackState === 4) {
      navigate("/prediction-track");
      return;
    }
    setTrackState(1);
    try {
      const res = await addTracking("stock", stockQuery);
      if (res.data.code === 409) {
        stopTrackCycle();
        setTrackState(4);
        return;
      }
      startTrackCycle();
    } catch {
      setTrackState(0);
    }
  }

  function toggleSection(key: string) {
    setSections((prev) => prev.map((s) => (s.key === key ? { ...s, collapsed: !s.collapsed } : s)));
  }

  useEffect(() => {
    async function fetchAnalysis() {
      setLoading(true);
      setError("");
      try {
        const res = await sendChat(stockQuery);
        const data = res.data.data;
        const content = data?.content || "";
        setIsCached(!!data?.cached);
        setSections(parseContent(content));
      } catch {
        setError("请求失败，请确认后端服务已启动");
      } finally {
        setLoading(false);
      }
    }
    fetchAnalysis();
    return () => stopTrackCycle();
  }, [stockQuery]);

  return (
    <div className="min-h-[calc(100vh-56px)] p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-semibold text-foreground tracking-tight">{stockQuery}</h2>
          <a href={`/prediction/${stockQuery}`} className="inline-flex items-center gap-1 mt-1.5 text-sm text-primary hover:opacity-80 transition-opacity">
            <Sparkles className="h-3.5 w-3.5" />
            AI 预测
          </a>
        </div>
        <div className="flex items-center gap-2">
          <button
            className={`relative inline-flex items-center h-9 px-4 rounded-lg text-sm font-medium border overflow-hidden transition-colors select-none outline-none ${trackBtnClass}`}
            disabled={trackState === 1}
            onClick={addToTracking}
          >
            <Crosshair className="h-4 w-4 mr-1.5 shrink-0" />
            <span className="relative overflow-hidden" style={{ width: 56, height: "1.25rem" }}>
              <span
                className="flex flex-col transition-transform duration-500"
                style={{ transform: `translateY(-${trackTextOffset})` }}
              >
                <span className="h-5 leading-5">加入跟踪</span>
                <span className="h-5 leading-5">发送中</span>
                <span className="h-5 leading-5">已发送</span>
                <span className="h-5 leading-5">跟踪中</span>
                <span className="h-5 leading-5">已跟踪</span>
              </span>
            </span>
          </button>
          <Button variant="outline" size="sm" className="rounded-lg" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            返回
          </Button>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-24">
          <p className="text-sm text-muted-foreground">AI 正在分析...</p>
        </div>
      )}

      {error && (
        <div className="flex items-center justify-center py-24">
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
      )}

      {!loading && !error && sections.length > 0 && (
        <div className="max-w-[820px] mx-auto">
          {isCached && (
            <div className="flex justify-end mb-3">
              <span className="text-xs text-muted-foreground/60 bg-muted/40 px-2 py-1 rounded-md">缓存结果</span>
            </div>
          )}
          <div className="flex flex-col gap-4">
            {sections.map((section) => {
              const Icon = section.icon;
              return (
                <div
                  key={section.key}
                  className={`bg-card rounded-lg border overflow-hidden ${
                    section.collapsed ? "border-border/40" : section.borderClass
                  }`}
                >
                  <button
                    className={`flex items-center justify-between w-full px-6 py-4 text-left transition-colors duration-200 group ${
                      section.collapsed ? "hover:bg-muted/20" : `${section.bgClass} ${section.textClass}`
                    }`}
                    onClick={() => toggleSection(section.key)}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex items-center justify-center h-9 w-9 rounded-lg transition-all duration-200 ${
                          section.collapsed ? "bg-muted/40" : "bg-white/60"
                        }`}
                      >
                        <Icon className={`h-4 w-4 transition-colors duration-200 ${section.collapsed ? "text-muted-foreground/50" : section.textClass}`} />
                      </div>
                      <span className={`text-[15px] font-medium ${section.collapsed ? "text-foreground/60" : "text-current"}`}>
                        {section.title}
                      </span>
                    </div>
                    <ChevronDown
                      className={`h-4 w-4 transition-transform duration-200 shrink-0 ${section.collapsed ? "text-muted-foreground/40" : "text-current/60"} ${
                        !section.collapsed ? "rotate-180" : ""
                      }`}
                    />
                  </button>
                  {!section.collapsed && (
                    <div className="px-8 pb-6 pt-1">
                      <div className="border-t border-border/30 pt-4" />
                      <div
                        className="prose prose-sm max-w-none prose-p:text-foreground/75 prose-headings:text-foreground/90 prose-strong:text-foreground/85 prose-li:text-foreground/75 prose-a:text-primary [&_h3]:text-base [&_h3]:font-medium [&_h3]:mb-2 [&_h3]:mt-4 [&_h3:first-child]:mt-0 [&_p]:my-2 [&_p]:leading-relaxed [&_ul]:my-2 [&_li]:my-1 [&_li]:leading-relaxed [&_h4]:text-sm [&_h4]:font-medium [&_h4]:mb-1.5 [&_h4]:mt-3"
                        dangerouslySetInnerHTML={{ __html: section.html }}
                      />
                      <div className="mt-4 pt-4 border-t border-border/20">
                        <a
                          href={`/deep-analysis/${stockQuery}/${section.title}`}
                          className={`inline-flex items-center gap-1.5 text-xs font-medium rounded-md px-3 py-1.5 border transition-colors hover:opacity-80 ${section.textClass} ${section.borderClass}`}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Sparkles className="h-3 w-3" />
                          深度分析{section.title}
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default StockDetail;
