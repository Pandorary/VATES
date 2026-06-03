import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  getHoldings,
  createHolding,
  updateHolding,
  deleteHolding,
  diagnoseHolding,
  refreshHoldingPrice,
  getTotalAssets,
  updateTotalAssets,
  type Holding,
} from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Plus, Pencil, Trash2, Stethoscope, Loader2, RotateCcw, X } from "lucide-react";
import { marked } from "marked";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

marked.setOptions({ breaks: true, gfm: true });

// ── Sheet (side drawer using @radix-ui/react-dialog) ──────────────

const sideClasses: Record<string, string> = {
  right:
    "right-0 top-0 h-full w-full max-w-[35vw] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right",
  left: "left-0 top-0 h-full w-full max-w-[35vw] data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:slide-out-to-left data-[state=open]:slide-in-from-left",
  top: "top-0 left-0 right-0 w-full data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:slide-out-to-top data-[state=open]:slide-in-from-top",
  bottom:
    "bottom-0 left-0 right-0 w-full data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom",
};

interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  side?: "left" | "right" | "top" | "bottom";
  children: React.ReactNode;
}

function Sheet({ open, onOpenChange, side = "right", children }: SheetProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0"
        />
        <DialogPrimitive.Content
          className={cn(
            "fixed z-50 gap-4 bg-background duration-300",
            sideClasses[side],
          )}
        >
          {(side === "right" || side === "left") ? (
            <div className="flex flex-col h-full">{children}</div>
          ) : (
            children
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

function SheetHeader({ children }: { children: React.ReactNode }) {
  return <div className="px-6 py-4">{children}</div>;
}

function SheetBody({ children }: { children: React.ReactNode }) {
  return <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>;
}

// ── Helpers ────────────────────────────────────────────────────────

function formatMoney(v: number): string {
  return v.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function profitClass(v: number | null): string {
  if (v === null || v === 0) return "";
  return v > 0 ? "text-red-600" : "text-emerald-600";
}

// ── Watchlist Page ─────────────────────────────────────────────────

const Watchlist = () => {
  const [items, setItems] = useState<Holding[]>([]);
  const [selectedItems, setSelectedItems] = useState<Holding[]>([]);
  const selectAllRef = useRef<HTMLInputElement>(null);

  // Summary
  const totalMarketValue = useMemo(
    () =>
      items.reduce(
        (sum, t) => sum + (t.current_price !== null ? t.current_price * t.shares : 0),
        0,
      ),
    [items],
  );
  const totalProfit = useMemo(
    () => items.reduce((sum, t) => sum + (t.profit_amount || 0), 0),
    [items],
  );
  const [totalAssets, setTotalAssets] = useState(0);

  // Edit sheet
  const [editing, setEditing] = useState(false);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ code: "", cost_price: 0, shares: 0, total_assets: 0 });

  // Delete dialog
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Holding | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Batch delete dialog
  const [batchDeleteOpen, setBatchDeleteOpen] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);

  // Diagnosis sheet
  const [diagOpen, setDiagOpen] = useState(false);
  const [diagTarget, setDiagTarget] = useState<Holding | null>(null);
  const [diagLoading, setDiagLoading] = useState(false);
  const [diagContent, setDiagContent] = useState("");

  // Refresh
  const [refreshing, setRefreshing] = useState(false);

  // Total assets inline edit
  const [editingTotalAssets, setEditingTotalAssets] = useState(false);
  const [editingTotalAssetsValue, setEditingTotalAssetsValue] = useState(0);
  const totalAssetsInputRef = useRef<HTMLInputElement>(null);

  // ── Data fetching ──────────────────────────────────────────────

  const fetchList = useCallback(async () => {
    try {
      const res = await getHoldings();
      setItems(res.data.data.items);
    } catch {
      /* ignore */
    }
    try {
      const res = await getTotalAssets();
      setTotalAssets(res.data.data?.value || 0);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  // Keep "select all" checkbox indeterminate state in sync
  useEffect(() => {
    const el = selectAllRef.current;
    if (el) {
      el.indeterminate = selectedItems.length > 0 && selectedItems.length < items.length;
    }
  }, [selectedItems, items]);

  // ── Selection ───────────────────────────────────────────────────

  function toggleSelectItem(item: Holding) {
    setSelectedItems((prev) => {
      const idx = prev.findIndex((s) => s.id === item.id);
      if (idx > -1) {
        return prev.filter((s) => s.id !== item.id);
      }
      return [...prev, item];
    });
  }

  function toggleSelectAll() {
    if (selectedItems.length === items.length && items.length > 0) {
      setSelectedItems([]);
    } else {
      setSelectedItems([...items]);
    }
  }

  // ── Create / Edit ───────────────────────────────────────────────

  function openCreate() {
    setDetailId(null);
    setForm({ code: "", cost_price: 0, shares: 0, total_assets: 0 });
    setEditing(true);
  }

  function openEdit(t: Holding) {
    setDetailId(t.id);
    setForm({ code: t.code, cost_price: t.cost_price, shares: t.shares, total_assets: 0 });
    setEditing(true);
  }

  async function submit() {
    if (!form.code.trim()) {
      toast.error("股票代码不能为空");
      return;
    }
    if (form.cost_price < 0 || form.shares < 0 || form.total_assets < 0) {
      toast.error("成本价、持仓数量和总资产不能为负");
      return;
    }
    if (!detailId && form.total_assets <= 0) {
      toast.error("新增持仓时总资产必须大于0");
      return;
    }

    setSaving(true);
    try {
      if (detailId) {
        await updateHolding(detailId, { cost_price: form.cost_price, shares: form.shares });
      } else {
        await createHolding(form);
      }
      await fetchList();
      setEditing(false);
      toast.success("保存成功");
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        "操作失败";
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  }

  // ── Delete ──────────────────────────────────────────────────────

  function confirmDelete(t: Holding) {
    setDeleteTarget(t);
    setDeleteOpen(true);
  }

  async function doDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteHolding(deleteTarget.id);
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

  // ── Batch Delete ────────────────────────────────────────────────

  function confirmBatchDelete() {
    setBatchDeleteOpen(true);
  }

  async function doBatchDelete() {
    if (selectedItems.length === 0) return;
    const count = selectedItems.length;
    setBatchDeleting(true);
    try {
      await Promise.all(selectedItems.map((item) => deleteHolding(item.id)));
      setBatchDeleteOpen(false);
      setSelectedItems([]);
      await fetchList();
      toast.success(`成功删除 ${count} 项持仓`);
    } catch {
      toast.error("批量删除失败");
    } finally {
      setBatchDeleting(false);
    }
  }

  // ── Diagnosis ───────────────────────────────────────────────────

  async function openDiagnose(t: Holding) {
    setDiagTarget(t);
    setDiagOpen(true);
    setDiagContent("");
    setDiagLoading(true);
    try {
      const res = await diagnoseHolding(t.id);
      const html = marked.parse(res.data.data?.content || "暂无诊断结果");
      setDiagContent(typeof html === "string" ? html : "");
    } catch {
      toast.error("诊断失败");
      setDiagOpen(false);
    } finally {
      setDiagLoading(false);
    }
  }

  // ── Refresh price ───────────────────────────────────────────────

  async function refreshStock(t: Holding) {
    setRefreshing(true);
    try {
      await refreshHoldingPrice(t.id);
      toast.success(`${t.code} 刷新成功`);
      await fetchList();
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { message?: string } } })?.response?.data?.message ||
        "未知错误";
      toast.error(`${t.code} 刷新失败: ${msg}`);
    } finally {
      setRefreshing(false);
    }
  }

  // ── Total assets inline edit ────────────────────────────────────

  function editTotalAssets() {
    setEditingTotalAssetsValue(totalAssets);
    setEditingTotalAssets(true);
  }

  useEffect(() => {
    if (editingTotalAssets && totalAssetsInputRef.current) {
      totalAssetsInputRef.current.focus();
      totalAssetsInputRef.current.select();
    }
  }, [editingTotalAssets]);

  async function saveTotalAssets() {
    if (editingTotalAssetsValue < 0) {
      toast.error("总资产不能为负数");
      return;
    }
    try {
      await updateTotalAssets(editingTotalAssetsValue);
      setTotalAssets(editingTotalAssetsValue);
      setEditingTotalAssets(false);
      toast.success("总资产已保存");
    } catch {
      toast.error("保存失败");
    }
  }

  function cancelEditTotalAssets() {
    setEditingTotalAssets(false);
  }

  // ── Render ─────────────────────────────────────────────────────

  return (
    <div className="min-h-[calc(100vh-56px)] p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div>
            <h2 className="text-2xl font-semibold text-primary">我的持仓</h2>
            <p className="text-sm text-muted-foreground mt-1">管理持仓股，实时查看盈亏</p>
          </div>
          {selectedItems.length > 0 && (
            <div className="flex items-center gap-2">
              <Badge variant="secondary">已选择 {selectedItems.length} 项</Badge>
              <Button
                variant="destructive"
                size="sm"
                disabled={batchDeleting}
                onClick={confirmBatchDelete}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                批量删除
              </Button>
            </div>
          )}
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4 mr-2" />
          新增持仓
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Card className="p-4">
          <p className="text-xs text-muted-foreground mb-1">持仓数量</p>
          <p className="text-2xl font-semibold">{items.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground mb-1">总市值</p>
          <p className="text-2xl font-semibold">{formatMoney(totalMarketValue)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground mb-1">总盈亏</p>
          <p
            className={cn(
              "text-2xl font-semibold",
              totalProfit > 0
                ? "text-red-600"
                : totalProfit < 0
                  ? "text-emerald-600"
                  : "",
            )}
          >
            {totalProfit > 0 ? "+" : ""}
            {formatMoney(totalProfit)}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground mb-1">总资产（元）</p>
          <div onDoubleClick={editTotalAssets} className="cursor-pointer select-none">
            {!editingTotalAssets ? (
              <p className="text-2xl font-semibold">{formatMoney(totalAssets)}</p>
            ) : (
              <input
                ref={totalAssetsInputRef}
                type="number"
                value={editingTotalAssetsValue}
                onChange={(e) => setEditingTotalAssetsValue(Number(e.target.value))}
                onBlur={saveTotalAssets}
                onKeyDown={(e) => {
                  if (e.key === "Enter") saveTotalAssets();
                  if (e.key === "Escape") cancelEditTotalAssets();
                }}
                className="w-40 h-9 rounded-md border border-input bg-background px-3 text-sm text-2xl font-semibold"
              />
            )}
          </div>
        </Card>
      </div>

      {/* Table */}
      <Card>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/30 [&>th]:text-foreground">
                <TableHead className="h-10 px-4 text-sm font-semibold text-center whitespace-nowrap">
                  <input
                    ref={selectAllRef}
                    type="checkbox"
                    className="rounded border-primary text-primary focus:ring-primary"
                    checked={selectedItems.length === items.length && items.length > 0}
                    onChange={toggleSelectAll}
                  />
                </TableHead>
                <TableHead className="h-10 px-4 text-sm font-semibold text-center whitespace-nowrap">
                  序号
                </TableHead>
                <TableHead className="h-10 px-4 text-sm font-semibold">代码</TableHead>
                <TableHead className="h-10 px-4 text-sm font-semibold">名称</TableHead>
                <TableHead className="h-10 px-4 text-sm font-semibold text-right">
                  成本价
                </TableHead>
                <TableHead className="h-10 px-4 text-sm font-semibold text-right">
                  现价
                </TableHead>
                <TableHead className="h-10 px-4 text-sm font-semibold text-right">
                  持仓数量
                </TableHead>
                <TableHead className="h-10 px-4 text-sm font-semibold text-right">
                  盈亏金额
                </TableHead>
                <TableHead className="h-10 px-4 text-sm font-semibold text-right">
                  盈亏%
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
                    <input
                      type="checkbox"
                      className="rounded border-primary text-primary focus:ring-primary"
                      checked={selectedItems.some((s) => s.id === t.id)}
                      onChange={() => toggleSelectItem(t)}
                    />
                  </TableCell>
                  <TableCell className="text-center text-sm text-muted-foreground">
                    {idx + 1}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="text-xs">
                      {t.code}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium text-sm">{t.name || "-"}</TableCell>
                  <TableCell className="text-right text-sm">
                    {t.cost_price?.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right text-sm">
                    {t.current_price !== null ? t.current_price.toFixed(2) : "-"}
                  </TableCell>
                  <TableCell className="text-right text-sm">{t.shares}</TableCell>
                  <TableCell className={cn("text-right text-sm", profitClass(t.profit_amount))}>
                    {t.profit_amount !== null
                      ? (t.profit_amount > 0 ? "+" : "") + t.profit_amount.toFixed(2)
                      : "-"}
                  </TableCell>
                  <TableCell className={cn("text-right text-sm", profitClass(t.profit_pct))}>
                    {t.profit_pct !== null
                      ? (t.profit_pct > 0 ? "+" : "") + t.profit_pct.toFixed(2) + "%"
                      : "-"}
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => openDiagnose(t)}
                        title="AI 诊断"
                      >
                        <Stethoscope className="h-4 w-4 text-primary" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => refreshStock(t)}
                        disabled={refreshing}
                        title={refreshing ? "刷新中..." : "刷新股价"}
                      >
                        {refreshing ? (
                          <Loader2 className="h-4 w-4 text-primary animate-spin" />
                        ) : (
                          <RotateCcw className="h-4 w-4 text-primary" />
                        )}
                      </Button>
                      <Button size="icon" variant="ghost" onClick={() => openEdit(t)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
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
            <p className="text-sm text-muted-foreground mb-2">还没有持仓记录</p>
            <p className="text-xs text-muted-foreground/70 mb-6">添加持仓股，跟踪盈亏</p>
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4 mr-2" />
              新增持仓
            </Button>
          </div>
        )}
      </Card>

      {/* ── Edit Sheet ──────────────────────────────────────────────── */}
      <Sheet open={editing} onOpenChange={(v) => { if (!v) setEditing(false); }}>
        <SheetHeader>
          <div className="flex items-center justify-between w-full">
            <div>
              <DialogPrimitive.Title className="text-base font-semibold">
                {detailId ? "编辑持仓" : "新增持仓"}
              </DialogPrimitive.Title>
              <p className="text-xs text-muted-foreground mt-0.5">填写持仓股信息</p>
            </div>
            <Button size="sm" disabled={saving} onClick={submit}>
              {saving ? "保存中..." : "保存"}
            </Button>
          </div>
        </SheetHeader>
        <SheetBody>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium text-muted-foreground">
                股票代码 <span className="text-destructive">*</span>
              </label>
              <Input
                value={form.code}
                onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
                placeholder="如 600519"
                disabled={!!detailId}
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium text-muted-foreground">
                成本价 <span className="text-destructive">*</span>
              </label>
              <Input
                type="number"
                step="0.01"
                value={form.cost_price || ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, cost_price: Number(e.target.value) }))
                }
                placeholder="如 1680.00"
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-xs font-medium text-muted-foreground">
                持仓数量（股） <span className="text-destructive">*</span>
              </label>
              <Input
                type="number"
                step="100"
                value={form.shares || ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, shares: Number(e.target.value) }))
                }
                placeholder="如 100"
              />
            </div>
            {!detailId && (
              <div className="flex flex-col gap-2">
                <label className="text-xs font-medium text-muted-foreground">
                  总资产（元） <span className="text-destructive">*</span>
                </label>
                <Input
                  type="number"
                  step="10000"
                  value={form.total_assets || ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, total_assets: Number(e.target.value) }))
                  }
                  placeholder="如 100000"
                />
              </div>
            )}
          </div>
        </SheetBody>
      </Sheet>

      {/* ── Diagnosis Sheet ─────────────────────────────────────────── */}
      <Sheet open={diagOpen} onOpenChange={(v) => { if (!v) setDiagOpen(false); }}>
        <SheetHeader>
          <div className="flex items-center justify-between w-full">
            <div>
              <DialogPrimitive.Title className="text-base font-semibold">
                AI 诊断
              </DialogPrimitive.Title>
              <p className="text-xs text-muted-foreground mt-0.5">
                {diagTarget?.name || diagTarget?.code}
                {diagTarget && (
                  <span
                    className={cn(
                      "ml-2",
                      (diagTarget.profit_amount ?? 0) > 0
                        ? "text-red-600"
                        : (diagTarget.profit_amount ?? 0) < 0
                          ? "text-emerald-600"
                          : "",
                    )}
                  >
                    {(diagTarget.profit_pct ?? 0) > 0 ? "+" : ""}
                    {diagTarget.profit_pct?.toFixed(2)}%
                  </span>
                )}
              </p>
            </div>
            <Button size="sm" variant="outline" onClick={() => setDiagOpen(false)}>
              关闭
            </Button>
          </div>
        </SheetHeader>
        <SheetBody>
          {diagLoading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground mr-2" />
              <span className="text-sm text-muted-foreground">AI 诊断中...</span>
            </div>
          ) : diagContent ? (
            <div
              className="prose prose-sm max-w-none prose-p:text-foreground/75 prose-headings:text-foreground/90 prose-strong:text-foreground/85 prose-li:text-foreground/75 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-6 [&_h2]:mb-3 [&_h3]:text-sm [&_h3]:font-medium [&_h3]:mb-1.5 [&_p]:my-1.5 [&_p]:leading-relaxed [&_li]:my-0.5"
              dangerouslySetInnerHTML={{ __html: diagContent }}
            />
          ) : null}
        </SheetBody>
      </Sheet>

      {/* ── Delete Dialog ──────────────────────────────────────────── */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription className="sr-only">确认删除持仓</DialogDescription>
          </DialogHeader>
          <p className="text-sm text-muted-foreground leading-relaxed">
            确定要删除「{deleteTarget?.name || deleteTarget?.code}」的持仓吗？删除后不可恢复。
          </p>
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
            <Button variant="destructive" size="sm" disabled={deleting} onClick={doDelete}>
              {deleting ? "删除中..." : "确认删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Batch Delete Dialog ────────────────────────────────────── */}
      <Dialog open={batchDeleteOpen} onOpenChange={setBatchDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认批量删除</DialogTitle>
            <DialogDescription className="sr-only">确认批量删除持仓</DialogDescription>
          </DialogHeader>
          <p className="text-sm text-muted-foreground leading-relaxed">
            确定要删除选中的 {selectedItems.length} 项持仓吗？删除后不可恢复。
          </p>
          {selectedItems.length > 0 && (
            <div className="mt-3 max-h-32 overflow-y-auto space-y-1">
              {selectedItems.map((item) => (
                <p key={item.id} className="text-xs text-muted-foreground">
                  &bull; {item.code} {item.name}
                </p>
              ))}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setBatchDeleteOpen(false)}>
              取消
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={batchDeleting}
              onClick={doBatchDelete}
            >
              {batchDeleting ? "删除中..." : "确认批量删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Watchlist;
