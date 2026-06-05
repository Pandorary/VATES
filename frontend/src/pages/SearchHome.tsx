import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { searchClassify } from "@/services/api";
import { Search, Clock, X } from "lucide-react";
import { loadHistory, saveHistory, appendHistory } from "./search/shared";

const SearchHome = () => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [searchHistory, setSearchHistory] = useState<string[]>(loadHistory);
  const [showHistory, setShowHistory] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  const navigate = useNavigate();

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowHistory(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  async function handleSearch(override?: string) {
    const q = (override ?? query).trim();
    if (!q) return;
    setLoading(true);
    setError("");
    setShowHistory(false);
    try {
      const res = await searchClassify(q);
      const data = res.data.data;
      if (data.type === "stock") {
        setSearchHistory(appendHistory(q));
        navigate(`/classify?q=${encodeURIComponent(q)}&type=stock&name=${encodeURIComponent(data.name)}`);
      } else if (data.type === "industry") {
        setSearchHistory(appendHistory(q));
        navigate(`/classify?q=${encodeURIComponent(q)}&type=industry&name=${encodeURIComponent(data.name)}`);
      } else {
        setError("未查询到相关标的信息，请核对名称或代码");
      }
    } catch {
      setError("请求失败，请确认后端服务已启动");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-center justify-center gap-5 pt-28 pb-20 px-4">
      {/* 标题 */}
      <div className="flex items-center gap-2 mb-1">
        <h1 className="text-[32px] font-medium text-black">VATES</h1>
      </div>

      {/* 搜索框 */}
      <div className="w-[460px] max-w-[90vw] relative" ref={searchContainerRef}>
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 h-4 w-4" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          onFocus={() => searchHistory.length > 0 && setShowHistory(true)}
          placeholder="搜索股票代码或名称"
          className="flex h-11 w-full rounded-xl border border-gray-300 bg-white pl-10 pr-4 text-[15px] text-gray-900 placeholder:text-gray-400 outline-none transition-all focus:ring-2 focus:ring-primary/20 focus:border-primary"
          disabled={loading}
        />

        {/* 搜索历史下拉 */}
        {showHistory && searchHistory.length > 0 && (
          <div className="absolute top-full mt-2 w-full bg-white rounded-xl border border-gray-200 shadow-lg overflow-hidden z-50">
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
              <span className="text-xs text-gray-400">最近搜索</span>
              <button
                className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
                onClick={() => { setSearchHistory([]); saveHistory([]); setShowHistory(false); }}
              >
                清除记录
              </button>
            </div>
            <div className="max-h-[280px] overflow-y-auto">
              {searchHistory.map((item, i) => (
                <button
                  key={`${item}-${i}`}
                  className="flex items-center justify-between w-full h-10 px-4 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                  onClick={() => { setQuery(item); setShowHistory(false); handleSearch(item); }}
                >
                  <span className="flex items-center gap-2 truncate">
                    <Clock className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                    <span className="truncate">{item}</span>
                  </span>
                  <button
                    className="ml-2 shrink-0 text-gray-300 hover:text-gray-500 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      const next = searchHistory.filter((_, j) => j !== i);
                      setSearchHistory(next);
                      saveHistory(next);
                    }}
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 搜索状态 */}
      {loading && (
        <p className="text-sm text-gray-400 mt-1">AI 正在识别...</p>
      )}
      {error && (
        <p className="text-sm text-gray-400 mt-1">{error}</p>
      )}
    </div>
  );
};

export default SearchHome;
