import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { deepAnalysis } from "@/services/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2 } from "lucide-react";
import { marked } from "marked";

marked.setOptions({ breaks: true, gfm: true });

const DeepAnalysis = () => {
  const { stock: stockQuery = "", section: sectionTitle = "" } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [content, setContent] = useState("");

  useEffect(() => {
    fetchAnalysis();
  }, []);

  async function fetchAnalysis() {
    setLoading(true);
    try {
      const res = await deepAnalysis(stockQuery, sectionTitle);
      const raw = res.data.data?.content || "";
      setContent(marked.parse(raw) as string);
    } catch {
      setError("深度分析请求失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-[calc(100vh-56px)] p-8">
      <div className="max-w-[820px] mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-semibold text-foreground tracking-tight">{sectionTitle}</h2>
            <p className="text-sm text-muted-foreground mt-1.5">{stockQuery} · 深度分析</p>
          </div>
          <Button variant="outline" size="sm" className="rounded-lg" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4 mr-1.5" />
            返回
          </Button>
        </div>

        {loading && (
          <div className="flex items-center gap-3 py-16 justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-sm text-muted-foreground">AI 正在对「{sectionTitle}」进行深度分析...</span>
          </div>
        )}

        {error && (
          <div className="text-center py-16">
            <p className="text-sm text-muted-foreground">{error}</p>
          </div>
        )}

        {!loading && !error && content && (
          <Card className="p-8 rounded-lg">
            <div
              className="prose prose-sm max-w-none prose-p:text-foreground/75 prose-headings:text-foreground/90 prose-strong:text-foreground/85 prose-li:text-foreground/75 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mt-6 [&_h2]:mb-3 [&_h3]:text-base [&_h3]:font-medium [&_h3]:mt-4 [&_h3]:mb-2 [&_p]:my-2 [&_p]:leading-relaxed [&_ul]:my-2 [&_li]:my-1"
              dangerouslySetInnerHTML={{ __html: content }}
            />
          </Card>
        )}
      </div>
    </div>
  );
};

export default DeepAnalysis;
