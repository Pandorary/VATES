import { useState, useEffect, useCallback, useMemo } from "react";
import { marked } from "marked";
import {
  getPromptTemplates,
  createPromptTemplate,
  updatePromptTemplate,
  deletePromptTemplate,
  copyPromptTemplate,
  type PromptTemplate,
} from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip";
import { Search, Plus, Pencil, Trash2, Copy } from "lucide-react";
import { toast } from "sonner";

marked.setOptions({ breaks: true, gfm: true });

// ── Options ──────────────────────────────────────────────────────────
const sceneOptions = [
  { label: "内容智能分类", value: "content_classify" },
  { label: "数据提取与校验", value: "data_extraction" },
  { label: "个股预测-下一交易日", value: "stock_prediction_tomorrow" },
  { label: "个股预测-一周", value: "stock_prediction_week" },
  { label: "个股预测-1个月", value: "stock_prediction_1m" },
  { label: "个股预测-3个月", value: "stock_prediction_3m" },
  { label: "行业研判", value: "industry_analysis" },
  { label: "个股复盘-下一交易日", value: "stock_review_tomorrow" },
  { label: "个股复盘-一周", value: "stock_review_week" },
  { label: "个股复盘-1个月", value: "stock_review_1m" },
  { label: "个股复盘-3个月", value: "stock_review_3m" },
  { label: "行业复盘校验", value: "industry_review" },
  { label: "持仓智能诊断", value: "position_diagnosis" },
  { label: "持仓复盘校验", value: "position_review" },
];

const moduleOptions = [
  { label: "个股分析", value: "stock_analysis" },
  { label: "深度分析", value: "deep_analysis" },
  { label: "AI 预测", value: "prediction" },
  { label: "通用", value: "general" },
];

const sceneFilterOptions = [
  { label: "全部业务场景", value: "all" },
  ...sceneOptions,
];

const moduleFilterOptions = [
  { label: "全部功能模块", value: "all" },
  ...moduleOptions,
];

const statusOptions = [
  { label: "全部状态", value: "all" },
  { label: "已启用", value: "1" },
  { label: "已停用", value: "0" },
];

function moduleLabel(value: string | undefined): string {
  if (!value) return "";
  return moduleOptions.find((o) => o.value === value)?.label || value;
}

function sceneLabel(value: string | undefined): string {
  if (!value) return "";
  return sceneOptions.find((o) => o.value === value)?.label || value;
}

// ── autoFormatMarkdown ───────────────────────────────────────────────
function autoFormatMarkdown(text: string): string {
  if (
    /^#{1,3}\s/m.test(text) ||
    /```/.test(text) ||
    /\*\*/.test(text) ||
    /^\s*[-*]\s/m.test(text)
  ) {
    return text;
  }
  const lines = text.split("\n");
  const result: string[] = [];
  let inJson = false;
  let jsonBuf: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!inJson && /^\s*\{/.test(line) && /"/.test(line)) {
      inJson = true;
      jsonBuf = [line];
      continue;
    }
    if (inJson) {
      jsonBuf.push(line);
      if (
        /^\s*\}\s*$/.test(line) ||
        (/\}\s*$/.test(line) && !/\{/.test(line))
      ) {
        result.push("```json");
        result.push(...jsonBuf);
        result.push("```");
        inJson = false;
        jsonBuf = [];
        continue;
      }
      continue;
    }
    const trimmed = line.trim();
    if (
      trimmed &&
      /^[研技基资风综注]/.test(trimmed) &&
      trimmed.length < 20 &&
      /[：:：]/.test(trimmed)
    ) {
      result.push("**" + trimmed + "**");
      continue;
    }
    result.push(line);
  }
  if (inJson && jsonBuf.length) {
    result.push("```json");
    result.push(...jsonBuf);
    result.push("```");
  }
  return result.join("\n");
}

// ── Sheet overlay (side drawer) built on @radix-ui/react-dialog ─────
function SheetOverlay({ className }: { className?: string }) {
  return (
    <DialogPrimitive.Overlay
      className={
        "fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 " +
        (className || "")
      }
    />
  );
}

// ── Form type ────────────────────────────────────────────────────────
interface FormState {
  scene: string;
  role: string;
  role_name: string;
  module: string;
  skill: string;
  skill_summary: string;
  skill_detail: string;
  is_active: boolean;
}

const initialForm: FormState = {
  scene: "",
  role: "",
  role_name: "",
  module: "",
  skill: "",
  skill_summary: "",
  skill_detail: "",
  is_active: true,
};

// ── Main Component ───────────────────────────────────────────────────
export default function PromptManager() {
  // List state
  const [items, setItems] = useState<PromptTemplate[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Filter state
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterModule, setFilterModule] = useState("all");
  const [filterScene, setFilterScene] = useState("all");
  const [searchText, setSearchText] = useState("");

  // Selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Preview
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewData, setPreviewData] = useState<PromptTemplate | null>(null);

  // Edit sheet
  const [sheetOpen, setSheetOpen] = useState(false);
  const [detailId, setDetailId] = useState("");
  const [saving, setSaving] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [form, setForm] = useState<FormState>({ ...initialForm });

  // Delete dialog
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<PromptTemplate | null>(null);
  const [deleting, setDeleting] = useState(false);

  // ── Fetch list ───────────────────────────────────────────────────
  const fetchList = useCallback(async () => {
    try {
      const res = await getPromptTemplates({
        page,
        page_size: pageSize,
        search: searchText || undefined,
        module: filterModule !== "all" ? filterModule : undefined,
        scene: filterScene !== "all" ? filterScene : undefined,
      });
      const data = res.data.data;
      setItems(data.items);
      setTotal(data.total);
    } catch {
      /* ignore */
    }
  }, [page, searchText, filterModule, filterScene]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  // ── Derived ──────────────────────────────────────────────────────
  const totalPages = Math.ceil(total / pageSize);

  const isAllSelected =
    items.length > 0 && items.every((t) => selectedIds.has(t.id));

  const previewContent = previewData?.skill_detail || "";
  const previewHtml = useMemo(
    () => marked(previewContent) as string,
    [previewContent],
  );

  // ── Helpers ──────────────────────────────────────────────────────
  function getSkillSummary(detail: string | undefined): string {
    if (!detail) return "";
    const text = detail.replace(/^\n/, "");
    return text.slice(0, 30);
  }

  // ── Selection handlers ───────────────────────────────────────────
  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (isAllSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((t) => t.id)));
    }
  }

  // ── Batch actions ────────────────────────────────────────────────
  async function batchToggle(active: boolean) {
    try {
      for (const id of selectedIds) {
        await updatePromptTemplate(id, { is_active: active });
      }
      setSelectedIds(new Set());
      await fetchList();
      toast.success(active ? "批量启用成功" : "批量停用成功");
    } catch {
      toast.error("批量操作失败");
    }
  }

  function batchDeleteConfirm() {
    setDeleteTarget(null);
    setDeleteOpen(true);
  }

  // ── Toggle active ────────────────────────────────────────────────
  async function toggleActive(t: PromptTemplate, newValue: boolean) {
    try {
      await updatePromptTemplate(t.id, { is_active: newValue });
      setItems((prev) =>
        prev.map((item) =>
          item.id === t.id ? { ...item, is_active: newValue } : item,
        ),
      );
    } catch {
      toast.error("操作失败");
    }
  }

  // ── Preview ──────────────────────────────────────────────────────
  function openPreview(t: PromptTemplate) {
    setPreviewData(t);
    setPreviewOpen(true);
  }

  async function copyPreview() {
    try {
      await navigator.clipboard.writeText(previewContent);
      toast.success("已复制到剪贴板");
    } catch {
      toast.error("复制失败");
    }
  }

  // ── Create / Edit ────────────────────────────────────────────────
  function openCreate() {
    setDetailId("");
    setForm({ ...initialForm });
    setSheetOpen(true);
    setIsFullscreen(false);
  }

  function openEdit(t: PromptTemplate) {
    setDetailId(t.id);
    setForm({
      scene: t.scene || "",
      role: t.role || "",
      role_name: t.role_name || "",
      module: t.module || "",
      skill: t.skill || "",
      skill_summary: t.skill_summary || "",
      skill_detail: t.skill_detail || "",
      is_active: t.is_active,
    });
    setSheetOpen(true);
    setIsFullscreen(false);
  }

  function closeDrawer() {
    setSheetOpen(false);
    setIsFullscreen(false);
  }

  function updateForm<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function submit() {
    if (!form.role_name.trim()) {
      toast.error("角色名称不能为空");
      return;
    }
    if (!form.scene.trim()) {
      toast.error("业务场景不能为空");
      return;
    }
    if (!form.skill_detail.trim()) {
      toast.error("模板内容不能为空");
      return;
    }
    const formatted = autoFormatMarkdown(form.skill_detail);
    if (formatted !== form.skill_detail) {
      setForm((prev) => ({ ...prev, skill_detail: formatted }));
      toast.success("模板内容已自动格式化为 Markdown");
    }
    setSaving(true);
    try {
      if (detailId) {
        await updatePromptTemplate(detailId, {
          scene: form.scene,
          role: form.role,
          role_name: form.role_name,
          module: form.module,
          skill: form.skill,
          skill_summary: form.skill_summary,
          skill_detail: formatted !== form.skill_detail ? formatted : form.skill_detail,
          is_active: form.is_active,
        });
      } else {
        await createPromptTemplate({
          scene: form.scene,
          role: form.role,
          role_name: form.role_name,
          module: form.module,
          skill: form.skill,
          skill_summary: form.skill_summary,
          skill_detail: formatted !== form.skill_detail ? formatted : form.skill_detail,
        });
      }
      await fetchList();
      setSheetOpen(false);
      setIsFullscreen(false);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { message?: string } } };
      toast.error(err?.response?.data?.message || "操作失败");
    } finally {
      setSaving(false);
    }
  }

  // ── Delete ───────────────────────────────────────────────────────
  function confirmDelete(t: PromptTemplate) {
    if (t.is_active) {
      toast.error("激活状态的模板不可删除，请先停用");
      return;
    }
    setDeleteTarget(t);
    setDeleteOpen(true);
  }

  // ── Copy ─────────────────────────────────────────────────────────
  async function copyTemplate(t: PromptTemplate) {
    try {
      await copyPromptTemplate(t.id);
      await fetchList();
      toast.success("复制成功");
    } catch {
      toast.error("复制失败");
    }
  }

  async function doDelete() {
    setDeleting(true);
    try {
      if (deleteTarget) {
        await deletePromptTemplate(deleteTarget.id);
      } else {
        for (const id of selectedIds) {
          await deletePromptTemplate(id);
        }
        setSelectedIds(new Set());
      }
      setDeleteOpen(false);
      setDeleteTarget(null);
      await fetchList();
      toast.success("删除成功");
    } catch {
      toast.error("删除失败");
    } finally {
      setDeleting(false);
    }
  }

  // ── Render ───────────────────────────────────────────────────────
  const hasFilter = searchText || filterStatus !== "all";

  return (
    <TooltipProvider>
      <div className="min-h-[calc(100vh-56px)] p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-primary">提示词管理</h2>
            <p className="text-sm text-muted-foreground mt-1">
              统一管理 AI 角色与提示词模板
            </p>
          </div>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" />
            新建模板
          </Button>
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-4 mb-6">
          {/* Scene filter */}
          <Select
            value={filterScene}
            onValueChange={(val) => {
              setFilterScene(val);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[170px]">
              <SelectValue placeholder="全部业务场景" />
            </SelectTrigger>
            <SelectContent>
              {sceneFilterOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Status filter */}
          <Select
            value={filterStatus}
            onValueChange={(val) => {
              setFilterStatus(val);
              fetchList();
            }}
          >
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="全部状态" />
            </SelectTrigger>
            <SelectContent>
              {statusOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Module filter */}
          <Select
            value={filterModule}
            onValueChange={(val) => {
              setFilterModule(val);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-[170px]">
              <SelectValue placeholder="全部功能模块" />
            </SelectTrigger>
            <SelectContent>
              {moduleFilterOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchText}
              placeholder="搜索角色、提示词关键词"
              className="w-[300px] pl-9 pr-8"
              onChange={(e) => setSearchText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") fetchList();
              }}
            />
            {searchText && (
              <button
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground rounded-md p-1.5 text-xs leading-none"
                onClick={() => {
                  setSearchText("");
                }}
              >
                &times;
              </button>
            )}
          </div>

          {/* Batch actions */}
          {selectedIds.size > 0 && (
            <div className="flex items-center gap-2 ml-auto">
              <Button
                variant="outline"
                size="sm"
                onClick={() => batchToggle(true)}
              >
                批量启用 ({selectedIds.size})
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => batchToggle(false)}
              >
                批量停用
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={batchDeleteConfirm}
              >
                批量删除
              </Button>
            </div>
          )}
        </div>

        {/* Table */}
        <Card>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30 [&>th]:text-foreground">
                  <TableHead className="h-10 px-4 text-sm font-semibold text-center whitespace-nowrap w-[40px]">
                    <Checkbox
                      checked={isAllSelected}
                      onCheckedChange={toggleAll}
                    />
                  </TableHead>
                  <TableHead className="h-10 px-4 text-sm font-semibold text-center whitespace-nowrap">
                    序号
                  </TableHead>
                  <TableHead className="h-10 px-4 text-sm font-semibold">
                    角色编码
                  </TableHead>
                  <TableHead className="h-10 px-4 text-sm font-semibold">
                    角色名称
                  </TableHead>
                  <TableHead className="h-10 px-4 text-sm font-semibold">
                    业务场景
                  </TableHead>
                  <TableHead className="h-10 px-4 text-sm font-semibold">
                    功能模块
                  </TableHead>
                  <TableHead className="h-10 px-4 text-sm font-semibold">
                    技能
                  </TableHead>
                  <TableHead className="h-10 px-4 text-sm font-semibold min-w-[200px]">
                    技能简介
                  </TableHead>
                  <TableHead className="h-10 px-4 text-sm font-semibold text-center">
                    状态
                  </TableHead>
                  <TableHead className="h-10 px-4 text-sm font-semibold">
                    更新时间
                  </TableHead>
                  <TableHead className="h-10 px-4 text-sm font-semibold text-center">
                    操作
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((t, idx) => (
                  <TableRow key={t.id} className="hover:bg-muted/50">
                    <TableCell className="text-center">
                      <Checkbox
                        checked={selectedIds.has(t.id)}
                        onCheckedChange={() => toggleSelect(t.id)}
                      />
                    </TableCell>
                    <TableCell className="text-center text-sm text-muted-foreground">
                      {(page - 1) * pageSize + idx + 1}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="secondary"
                        className="text-xs cursor-pointer hover:opacity-80"
                        onClick={() => openPreview(t)}
                      >
                        {t.role || "-"}
                      </Badge>
                    </TableCell>
                    <TableCell
                      className="font-medium text-sm cursor-pointer hover:opacity-80"
                      onClick={() => openPreview(t)}
                    >
                      {t.role_name || "-"}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {sceneLabel(t.scene) || "-"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {moduleLabel(t.module) || "-"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {t.skill || "-"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="truncate max-w-[280px] block cursor-default text-sm">
                            {getSkillSummary(t.skill_detail) || "-"}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>
                          <div className="text-sm leading-relaxed max-w-xs">
                            {t.skill_summary || "暂无技能名称"}
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    </TableCell>
                    <TableCell
                      className="text-center"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Switch
                        checked={t.is_active}
                        onCheckedChange={(val) => toggleActive(t, val)}
                      />
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                      {t.updated_at?.slice(0, 10) || "-"}
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => copyTemplate(t)}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => openEdit(t)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className={t.is_active ? "text-muted-foreground/30" : "text-destructive hover:text-destructive hover:bg-destructive/10"}
                          disabled={t.is_active}
                          onClick={() => confirmDelete(t)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Empty state */}
          {items.length === 0 && (
            <div className="text-center py-12">
              <p className="text-sm text-muted-foreground mb-2">
                {hasFilter
                  ? "没有匹配的模板"
                  : "还没有提示词模板"}
              </p>
              <p className="text-xs text-muted-foreground/70 mb-6">
                {hasFilter
                  ? "尝试调整筛选条件或搜索关键词"
                  : "创建第一个模板，开始自定义 AI 分析行为"}
              </p>
              {!hasFilter && (
                <Button onClick={openCreate}>
                  <Plus className="h-4 w-4 mr-2" />
                  新建模板
                </Button>
              )}
            </div>
          )}

          {/* Pagination */}
          {total > pageSize && (
            <div className="flex items-center justify-center gap-4 py-4 border-t">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                上一页
              </Button>
              <span className="text-sm text-muted-foreground">
                {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                下一页
              </Button>
              <span className="text-sm text-muted-foreground ml-2">
                共 {total} 条
              </span>
            </div>
          )}
        </Card>

        {/* ── Preview Dialog ────────────────────────────────────── */}
        <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>提示词模板预览</DialogTitle>
              <DialogDescription>
                {previewData?.role_name} / {previewData?.skill_summary}
              </DialogDescription>
            </DialogHeader>
            <div
              className="max-h-[60vh] overflow-auto rounded-md border bg-muted/30 p-4 prose prose-sm max-w-none [&_h2]:text-lg [&_h2]:font-bold [&_h2]:mt-6 [&_h2]:mb-3 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mt-4 [&_h3]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:my-2 [&_li]:my-0.5 [&_p]:my-2"
              dangerouslySetInnerHTML={{ __html: previewHtml }}
            />
            <DialogFooter>
              <Button variant="outline" size="sm" onClick={copyPreview}>
                一键复制
              </Button>
              <Button size="sm" onClick={() => setPreviewOpen(false)}>
                关闭
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* ── Edit Sheet (side drawer) ──────────────────────────── */}
        <DialogPrimitive.Root open={sheetOpen} onOpenChange={(v) => { if (!v) closeDrawer(); }}>
          <DialogPrimitive.Portal>
            <SheetOverlay />
            <DialogPrimitive.Content
              className={
                "fixed top-0 right-0 z-50 h-full bg-background transition-transform duration-300 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right flex flex-col " +
                (isFullscreen
                  ? "w-full inset-0"
                  : "w-[600px] max-w-[90vw]")
              }
            >
              {/* Sheet header */}
              <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
                <div>
                  <span className="text-base font-semibold">
                    {detailId ? "编辑模板" : "新建模板"}
                  </span>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    统一管理 AI 角色与提示词模板
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    disabled={saving}
                    onClick={submit}
                  >
                    {saving ? "保存中..." : "保存"}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsFullscreen((v) => !v)}
                  >
                    {isFullscreen ? "退出全屏" : "全屏"}
                  </Button>
                  <DialogPrimitive.Close asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <span className="text-lg leading-none">&times;</span>
                    </Button>
                  </DialogPrimitive.Close>
                </div>
              </div>

              {/* Sheet body */}
              <div className="flex-1 overflow-y-auto px-6 py-4">
                <div className="flex flex-col gap-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-2">
                      <label className="text-xs font-medium text-muted-foreground">
                        业务场景 <span className="text-destructive">*</span>
                      </label>
                      <Select
                        value={form.scene}
                        onValueChange={(val) => updateForm("scene", val)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="请选择业务场景" />
                        </SelectTrigger>
                        <SelectContent>
                          {sceneOptions.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                              {opt.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-xs font-medium text-muted-foreground">
                        角色编码
                      </label>
                      <Input
                        value={form.role}
                        placeholder="如 analyst"
                        onChange={(e) => updateForm("role", e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-2">
                      <label className="text-xs font-medium text-muted-foreground">
                        角色名称 <span className="text-destructive">*</span>
                      </label>
                      <Input
                        value={form.role_name}
                        placeholder="如 分析师"
                        onChange={(e) => updateForm("role_name", e.target.value)}
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-xs font-medium text-muted-foreground">
                        功能模块
                      </label>
                      <Select
                        value={form.module}
                        onValueChange={(val) => updateForm("module", val)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="请选择功能模块" />
                        </SelectTrigger>
                        <SelectContent>
                          {moduleOptions.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                              {opt.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-2">
                      <label className="text-xs font-medium text-muted-foreground">
                        技能编码
                      </label>
                      <Input
                        value={form.skill}
                        placeholder="如 stock_analysis"
                        onChange={(e) => updateForm("skill", e.target.value)}
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-xs font-medium text-muted-foreground">
                        技能名称
                      </label>
                      <Input
                        value={form.skill_summary}
                        placeholder="如 个股分析"
                        onChange={(e) =>
                          updateForm("skill_summary", e.target.value)
                        }
                      />
                    </div>
                  </div>

                  <Separator />

                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-medium text-muted-foreground">
                      技能详情 <span className="text-destructive">*</span>
                    </label>
                    <Textarea
                      value={form.skill_detail}
                      className="min-h-[800px] font-mono leading-relaxed"
                      placeholder="输入技能详情，支持 Markdown 格式..."
                      onChange={(e) =>
                        updateForm("skill_detail", e.target.value)
                      }
                    />
                  </div>

                  {detailId && (
                    <>
                      <Separator />
                      <div className="flex flex-col gap-2">
                        <label className="text-xs font-medium text-muted-foreground">
                          状态
                        </label>
                        <div className="flex items-center gap-2 py-1">
                          <Switch
                            checked={form.is_active}
                            onCheckedChange={(val) =>
                              updateForm("is_active", val)
                            }
                          />
                          <span
                            className={
                              "text-sm " +
                              (form.is_active
                                ? "text-primary"
                                : "text-muted-foreground")
                            }
                          >
                            {form.is_active ? "启用" : "停用"}
                          </span>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </DialogPrimitive.Content>
          </DialogPrimitive.Portal>
        </DialogPrimitive.Root>

        {/* ── Delete Dialog ─────────────────────────────────────── */}
        <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>确认删除</DialogTitle>
              <DialogDescription>
                {deleteTarget
                  ? `确定要删除「${deleteTarget.role_name}」的模板吗？删除后不可恢复。`
                  : `确定要删除选中的 ${selectedIds.size} 个模板吗？删除后不可恢复。`}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setDeleteOpen(false);
                  setDeleteTarget(null);
                }}
              >
                取消
              </Button>
              <Button
                variant="destructive"
                size="sm"
                disabled={deleting}
                onClick={doDelete}
              >
                {deleting ? "删除中..." : "确认删除"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  );
}
