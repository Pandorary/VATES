import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Sparkles } from "lucide-react";

const AIPredictionEntry = () => {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  function goPredict() {
    const v = query.trim();
    if (!v) return;
    navigate(`/prediction/${v}`);
  }

  return (
    <div className="flex flex-col items-center gap-4 py-10 pb-[25vh]">
      <div className="mb-2">
        <h1 className="text-4xl font-light tracking-[8px] text-foreground uppercase text-center">
          <span className="inline-flex items-center gap-3">
            <Sparkles className="h-7 w-7 text-primary" />
            AI 预测
          </span>
          <span className="block h-1 w-12 mx-auto mt-3 rounded-sm bg-primary/40"></span>
        </h1>
        <p className="text-sm text-muted-foreground text-center mt-3 tracking-normal">
          输入股票代码或名称，进行多时段 AI 推演
        </p>
      </div>

      <div className="relative w-[420px] max-w-[90vw] group">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground transition-colors group-focus-within:text-primary" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && goPredict()}
          placeholder="输入股票代码或名称..."
          className="flex h-11 w-full rounded-lg border border-input bg-background pl-11 pr-4 text-[15px] text-foreground placeholder:text-muted-foreground outline-none ring-offset-background transition-all focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
        />
      </div>
    </div>
  );
};

export default AIPredictionEntry;
