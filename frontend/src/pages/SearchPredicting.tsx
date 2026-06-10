import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { predictStock, predictIndustry } from "@/services/api";
import { Loader2 } from "lucide-react";
import { RESULT_CACHE_KEY, type PredResult } from "./search/shared";

const SearchPredicting = () => {
  const [searchParams] = useSearchParams();
  const type = searchParams.get("type") as "stock" | "industry" | null;
  const name = searchParams.get("name") || "";
  const horizon = searchParams.get("horizon") || "";

  const navigate = useNavigate();
  const calledRef = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!type || !name) {
      navigate("/", { replace: true });
      return;
    }
    if (type === "stock" && !horizon) {
      navigate("/", { replace: true });
      return;
    }
    if (calledRef.current) return;
    calledRef.current = true;

    (async () => {
      try {
        let res;
        if (type === "stock") {
          res = await predictStock(name, horizon);
        } else {
          res = await predictIndustry(name);
        }
        const data = res.data.data;

        if (res.data.code !== 200 && res.data.code !== 0) {
          setError(res.data.message || "AI 预测失败，请稍后重试");
          return;
        }

        const result: PredResult = {
          classifyType: type,
          classifyName: name,
          selectedHorizon: type === "industry" ? "short_long" : horizon,
          predContent: data.content || "",
          predConfidence: data.confidence || "",
          predDataSnapshot: data.data_snapshot || null,
        };

        sessionStorage.setItem(RESULT_CACHE_KEY, JSON.stringify(result));
        navigate(
          `/result?type=${type}&name=${encodeURIComponent(name)}&horizon=${encodeURIComponent(type === "industry" ? "short_long" : horizon)}`,
          { state: result, replace: true },
        );
      } catch {
        setError("请求失败，请确认后端服务已启动");
      }
    })();
  }, [type, name, horizon, navigate]);

  return (
    <div className="flex flex-col items-center justify-center gap-5 pt-28 pb-20 px-4">
      <h1 className="text-[32px] font-medium text-black">VATES</h1>
      {error ? (
        <div className="flex flex-col items-center gap-4 mt-10">
          <p className="text-sm text-gray-500">{error}</p>
          <Link to="/" className="text-sm text-primary hover:underline">返回首页重新搜索</Link>
        </div>
      ) : (
        <div className="flex items-center gap-3 mt-10">
          <Loader2 className="h-5 w-5 animate-spin text-primary" />
          <span className="text-sm text-gray-400">数据引擎获取中，AI 推演中...</span>
        </div>
      )}
    </div>
  );
};

export default SearchPredicting;
