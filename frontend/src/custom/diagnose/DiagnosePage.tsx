import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { RefreshCw, Trash2, ArrowUp, ArrowDown, ChevronsUpDown, Loader2, Search } from 'lucide-react'
import { useVirtualizer } from '@tanstack/react-virtual'

import { api } from '@/lib/api'
import { QK } from '@/lib/queryKeys'
import type { DiagnoseRow } from '@/lib/api'
import { VIRTUAL_LIST_THRESHOLD, useParentScroll } from '@/components/virtual-list/useParentScroll'
import DiagnoseDetailDialog from './DiagnoseDetailDialog'
import { useDiagnoseProgress } from './useDiagnoseProgress'

const num = (v: unknown): number | null =>
  typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : null
const fmt = (v: unknown, d = 2): string => {
  const n = num(v)
  return n === null || Number.isNaN(n) ? '—' : n.toFixed(d)
}
const fmtSigned = (v: unknown): string => {
  const n = num(v)
  if (n === null || Number.isNaN(n)) return '—'
  return `${n > 0 ? '+' : ''}${n.toFixed(2)}`
}
/** 按列名取快照行数值（含未知列安全访问）。 */
const colVal = (r: DiagnoseRow, col: string): unknown => (r as unknown as Record<string, unknown>)[col]

/** 财务同比差值（财务总分 - 上年同期）。 */
const finDiffOf = (r: DiagnoseRow): number | null => {
  const ft = num(colVal(r, 'finance_total'))
  const fp = num(colVal(r, 'finance_prev'))
  return ft !== null && fp !== null ? ft - fp : null
}

/** ST 判定：与项目既有口径一致（名称含 "ST"，含 *ST），见 price_limits / abnormal_moves。 */
const isStName = (name: string | null | undefined): boolean =>
  Boolean(name && name.toUpperCase().includes('ST'))

/** 分组矩阵：按诊股可用分值字段统计并排序（参考 概念/行业分析 的矩阵 rail）。 */
type MatrixSortKey = 'avg' | 'fund' | 'tech' | 'finance'
interface MatrixGroup {
  name: string
  rows: DiagnoseRow[]
  count: number
  avg: number
  fund: number
  tech: number
  finance: number
}
const groupStatOf = (rows: DiagnoseRow[]) => {
  const n = rows.length || 1
  const sum = (col: string) => rows.reduce((s, r) => s + (num(colVal(r, col)) ?? 0), 0) / n
  return { avg: sum('score_average'), fund: sum('score_fund'), tech: sum('score_tech'), finance: sum('score_finance') }
}
const groupVal = (g: MatrixGroup, key: MatrixSortKey): number =>
  key === 'avg' ? g.avg : key === 'fund' ? g.fund : key === 'tech' ? g.tech : g.finance
const sortGroups = (arr: MatrixGroup[], key: MatrixSortKey): MatrixGroup[] =>
  [...arr].sort((a, b) => groupVal(b, key) - groupVal(a, key) || b.count - a.count)

interface SortCol {
  key: string
  label: string
  kind: 'score' | 'signed' | 'rank'
}

const SORT_COLS: SortCol[] = [
  { key: 'score_fund', label: '资金', kind: 'score' },
  { key: 'score_tech', label: '技术', kind: 'score' },
  { key: 'score_valuation', label: '估值', kind: 'score' },
  { key: 'score_message', label: '消息', kind: 'score' },
  { key: 'score_finance', label: '财务', kind: 'score' },
  { key: 'score_average', label: '综合均', kind: 'score' },
  { key: 'fund_chg', label: '资金较昨', kind: 'signed' },
  { key: 'fin_diff', label: '财务同比', kind: 'signed' },
  { key: 'rank_industry', label: '行业排名', kind: 'rank' },
]

function HeaderCol({
  col,
  sortKey,
  sortDir,
  onSort,
  right,
  children,
}: {
  col?: SortCol
  sortKey: string | null
  sortDir: 'asc' | 'desc'
  onSort: (k: string) => void
  right?: boolean
  children: ReactNode
}) {
  const k = col?.key ?? null
  const active = k !== null && sortKey === k
  return (
    <th
      className={`px-2 py-1.5 text-xs font-medium text-muted whitespace-nowrap ${right ? 'text-right' : 'text-left'} ${
        k ? 'cursor-pointer select-none hover:text-foreground' : ''
      }`}
      onClick={k ? () => onSort(k) : undefined}
    >
      <span className="inline-flex items-center gap-0.5">
        {children}
        {k ? (
          active ? (
            sortDir === 'asc' ? (
              <ArrowUp size={11} />
            ) : (
              <ArrowDown size={11} />
            )
          ) : (
            <ChevronsUpDown size={11} className="opacity-50" />
          )
        ) : null}
      </span>
    </th>
  )
}

export default function DiagnosePage() {
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  const [includeTrend, setIncludeTrend] = useState(true)
  const [viewMode, setViewMode] = useState<'flat' | 'industry' | 'concept'>('flat')
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null)
  const [selectedConcept, setSelectedConcept] = useState<string | null>(null)
  const [matrixSort, setMatrixSort] = useState<MatrixSortKey>('avg')
  const [groupSearch, setGroupSearch] = useState('')
  const [chipFund, setChipFund] = useState(false)
  const [chipFin, setChipFin] = useState(false)
  const [stFilter, setStFilter] = useState<'all' | 'st' | 'non-st'>('all')
  const [sortKey, setSortKey] = useState<string | null>('score_average')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [notice, setNotice] = useState<string | null>(null)
  const [selected, setSelected] = useState<{ symbol: string; name?: string | null } | null>(null)

  const { data: cfg } = useQuery({
    queryKey: QK.diagnoseConfig,
    queryFn: () => api.thsDiagnoseConfig(),
  })
  const { data: snap } = useQuery({
    queryKey: QK.diagnoseSnapshot,
    queryFn: () => api.thsDiagnoseSnapshot(),
  })

  // 概念分类数据（扩展数据预置 ext_gn_ths，所属概念为分号拼接的多概念字段）
  const { data: conceptRows } = useQuery({
    queryKey: QK.extDataRows('ext_gn_ths', undefined, 20000, '所属概念'),
    queryFn: () => api.extDataRows('ext_gn_ths', { limit: 20000, columns: ['所属概念'] }),
    enabled: viewMode === 'concept',
    retry: false,
  })

  // 全局进度（页面 + 左侧菜单共用；切页不丢）
  const progressQ = useDiagnoseProgress()
  const progress = progressQ.data
  const running = Boolean(progress?.running)

  // 同步从进行中 -> 完成时（含在其它页面完成、回来即触发）：刷新快照并给出完成提示
  const prevRunning = useRef(running)
  useEffect(() => {
    const was = prevRunning.current
    prevRunning.current = running
    if (was && !running && progress?.total) {
      qc.invalidateQueries({ queryKey: QK.diagnoseConfig })
      qc.invalidateQueries({ queryKey: QK.diagnoseSnapshot })
      const failed = progress.failed_symbols ?? []
      setNotice(
        `拉取完成：成功 ${progress.ok ?? 0} / ${progress.total}，失败 ${progress.failed ?? 0}${
          failed.length ? `（可重试 ${failed.slice(0, 5).join('、')}…）` : ''
        }`,
      )
    }
  }, [running, progress, qc])

  // URL ?symbol=xxx → 打开详情（个股 K 线弹窗底部入口进入时使用）
  useEffect(() => {
    const s = searchParams.get('symbol')
    if (s) {
      setSelected({ symbol: s })
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams])

  // ---------------- A 股全量手动拉取 ----------------
  const doPull = async () => {
    setNotice(null)
    try {
      const r = await api.thsDiagnoseSnapshotPull([], includeTrend, 'all')
      setNotice(`已开始拉取 A 股全量 ${r.queued} 只，高并发执行`)
      await qc.invalidateQueries({ queryKey: QK.diagnoseConfig })
      await qc.invalidateQueries({ queryKey: QK.diagnoseProgress })
    } catch (e) {
      setNotice(e instanceof Error ? e.message : String(e))
    }
  }

  const clearSnapshot = async () => {
    await api.thsDiagnoseSnapshotClear()
    await qc.invalidateQueries({ queryKey: QK.diagnoseConfig })
    await qc.invalidateQueries({ queryKey: QK.diagnoseSnapshot })
  }

  // ---------------- 表格：快筛 → 排序 → 分组 ----------------
  const filtered = useMemo(() => {
    let rows = (snap?.rows ?? []) as DiagnoseRow[]
    if (chipFund) rows = rows.filter((r) => (num(colVal(r, 'fund_chg')) ?? -Infinity) > 0)
    if (chipFin) rows = rows.filter((r) => (finDiffOf(r) ?? -Infinity) > 0)
    if (stFilter === 'st') rows = rows.filter((r) => isStName(r.name))
    if (stFilter === 'non-st') rows = rows.filter((r) => !isStName(r.name))
    return rows
  }, [snap, chipFund, chipFin, stFilter])

  const sortValOf = (r: DiagnoseRow, key: string): number | null =>
    key === 'fin_diff' ? finDiffOf(r) : num(colVal(r, key))

  const sorted = useMemo(() => {
    const rows = [...filtered]
    if (!sortKey) return rows
    rows.sort((a, b) => {
      const av = sortValOf(a, sortKey)
      const bv = sortValOf(b, sortKey)
      if (av === null && bv === null) return 0
      if (av === null) return 1
      if (bv === null) return -1
      return sortDir === 'asc' ? av - bv : bv - av
    })
    return rows
  }, [filtered, sortKey, sortDir])

  const industries = useMemo<MatrixGroup[]>(() => {
    const map = new Map<string, DiagnoseRow[]>()
    for (const r of filtered) {
      const key = r.industry_name || '未分类'
      const arr = map.get(key)
      if (arr) arr.push(r)
      else map.set(key, [r])
    }
    return Array.from(map.entries())
      .map(([name, rows]) => ({ name, rows, count: rows.length, ...groupStatOf(rows) }))
      .sort((a, b) => b.count - a.count || b.avg - a.avg)
  }, [filtered])

  // 概念：code / 裸代码 → 概念列表（分号拼接字段拆分）
  const conceptMap = useMemo(() => {
    const m = new Map<string, string[]>()
    for (const row of conceptRows?.rows ?? []) {
      const code = String(row?.code ?? '').trim() || String(row?.symbol ?? '').split('.')[0].trim()
      if (!code) continue
      const cs = String(row?.所属概念 ?? '')
        .split(/[;；]/)
        .map((s) => s.trim())
        .filter(Boolean)
      if (cs.length) m.set(code, cs)
    }
    return m
  }, [conceptRows])

  const conceptsOf = (r: DiagnoseRow): string[] =>
    conceptMap.get(String(r.code ?? '')) ?? conceptMap.get(String(r.symbol ?? '').split('.')[0]) ?? []

  // 概念分组：一只股票可属于多个概念；无概念归属者归入「未分类」
  const concepts = useMemo<MatrixGroup[]>(() => {
    const map = new Map<string, DiagnoseRow[]>()
    for (const r of filtered) {
      const cs = conceptsOf(r)
      if (!cs.length) {
        const key = '未分类'
        const arr = map.get(key)
        if (arr) arr.push(r)
        else map.set(key, [r])
        continue
      }
      for (const c of cs) {
        const arr = map.get(c)
        if (arr) arr.push(r)
        else map.set(c, [r])
      }
    }
    return Array.from(map.entries())
      .map(([name, rows]) => ({ name, rows, count: rows.length, ...groupStatOf(rows) }))
      .sort((a, b) => b.count - a.count || b.avg - a.avg)
  }, [filtered, conceptMap])

  // 矩阵：搜索过滤 + 排序（参考 概念/行业分析 矩阵 rail）
  const shownIndustries = useMemo(() => {
    const q = groupSearch.trim()
    const list = q ? industries.filter((g) => g.name.includes(q)) : industries
    return sortGroups(list, matrixSort)
  }, [industries, groupSearch, matrixSort])
  const shownConcepts = useMemo(() => {
    const q = groupSearch.trim()
    const list = q ? concepts.filter((g) => g.name.includes(q)) : concepts
    return sortGroups(list, matrixSort)
  }, [concepts, groupSearch, matrixSort])

  const viewRows = useMemo(() => {
    if (viewMode === 'flat') return sorted
    if (viewMode === 'industry') {
      if (!selectedIndustry) return sorted
      return sorted.filter((r) => (r.industry_name || '未分类') === selectedIndustry)
    }
    if (!selectedConcept) return sorted
    if (selectedConcept === '未分类') return sorted.filter((r) => conceptsOf(r).length === 0)
    return sorted.filter((r) => conceptsOf(r).includes(selectedConcept))
  }, [sorted, viewMode, selectedIndustry, selectedConcept, conceptMap])

  // ---------------- 虚拟列表（大批量行时避免渲染全部 React 节点） ----------------
  const tableRef = useRef<HTMLTableElement>(null)
  const virtualized = viewRows.length > VIRTUAL_LIST_THRESHOLD
  const { getScrollElement, scrollMargin } = useParentScroll(tableRef, virtualized)
  const rowVirtualizer = useVirtualizer({
    count: virtualized ? viewRows.length : 0,
    getScrollElement,
    estimateSize: () => 40,
    getItemKey: (index) => viewRows[index].symbol,
    overscan: 12,
    scrollMargin,
  })
  const virtualRows = virtualized ? rowVirtualizer.getVirtualItems() : []
  const totalSize = virtualized ? rowVirtualizer.getTotalSize() : 0
  const firstVirtualRow = virtualRows[0]
  const lastVirtualRow = virtualRows[virtualRows.length - 1]
  const topPadding = firstVirtualRow ? firstVirtualRow.start - scrollMargin : 0
  const bottomPadding = lastVirtualRow
    ? totalSize - (lastVirtualRow.end - scrollMargin)
    : totalSize

  const onSort = (k: string) => {
    if (sortKey === k) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else {
      setSortKey(k)
      setSortDir('desc')
    }
  }

  const resetChips = () => {
    setChipFund(false)
    setChipFin(false)
    setStFilter('all')
  }

  const renderBodyRow = (r: DiagnoseRow, index: number): ReactNode => (
    <tr
      key={r.symbol}
      data-index={index}
      ref={virtualized ? rowVirtualizer.measureElement : undefined}
      onClick={() => setSelected({ symbol: r.symbol, name: r.name })}
      className="border-b border-border last:border-0 cursor-pointer hover:bg-elevated/70 transition-colors"
    >
      <td className="px-2 py-1.5 whitespace-nowrap">
        <span className="text-xs font-medium text-foreground">{r.name ?? r.symbol}</span>
        <span className="block text-[11px] font-mono text-muted">{r.symbol}</span>
      </td>
      {viewMode === 'flat' ? (
        <td className="px-2 py-1.5 text-xs text-muted whitespace-nowrap text-left">{r.industry_name ?? '—'}</td>
      ) : null}
      {SORT_COLS.map((c) => (
        <td key={c.key} className="px-2 py-1.5 font-mono tabular-nums whitespace-nowrap text-right">
          {renderNumCell(r, c)}
        </td>
      ))}
    </tr>
  )

  const renderNumCell = (r: DiagnoseRow, c: SortCol): ReactNode => {
    if (c.kind === 'rank') {
      const rank = num(colVal(r, 'rank_industry'))
      if (rank === null) return <span className="text-muted">—</span>
      return (
        <span className="text-muted">
          {rank}
          {num(colVal(r, 'total_industry')) !== null ? `/${num(colVal(r, 'total_industry'))}` : ''}
        </span>
      )
    }
    const v = num(sortValOf(r, c.key))
    if (c.kind === 'signed') {
      if (v === null || Number.isNaN(v)) return <span className="text-muted">—</span>
      return (
        <span className={v >= 0 ? 'text-bull' : 'text-bear'}>{fmtSigned(v)}</span>
      )
    }
    return <>{fmt(v)}</>
  }

  const total = snap?.total ?? 0

  return (
    <div className="p-4 space-y-4 max-w-[1400px] mx-auto">
      {/* 标题 */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-base font-medium text-foreground">智能诊股</h1>
          <p className="text-xs text-muted mt-0.5">
            标的范围：沪深 A 股全量 · 长线价值口径，财务分按财报披露周期更新，无需盘中刷新。
            {total > 0 && (
              <>
                {' '}
                当前快照 <span className="font-mono">{total}</span> 只 · 更新于{' '}
                <span className="font-mono">{cfg?.date ?? '—'}</span>
              </>
            )}
          </p>
        </div>
        {total > 0 && (
          <button
            type="button"
            onClick={clearSnapshot}
            className="inline-flex items-center gap-1.5 h-8 px-2.5 rounded-btn bg-elevated text-xs text-muted hover:text-danger transition-colors"
          >
            <Trash2 size={14} /> 清空快照
          </button>
        )}
      </div>

      {/* 拉取操作 */}
      <div className="rounded-card bg-surface border border-border px-4 py-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <p className="text-sm text-foreground">
            A 股全量（沪深，约 5k 只）<span className="text-xs text-muted">· 外部私有接口，高并发执行</span>
          </p>
          <div className="flex items-center gap-3 flex-wrap">
            <label className="inline-flex items-center gap-1.5 text-xs text-muted">
              <input
                type="checkbox"
                checked={includeTrend}
                onChange={(e) => setIncludeTrend(e.target.checked)}
                className="accent-[color:var(--color-accent)]"
              />
              含趋势列（资金较昨 + 财务同比；关闭则每只 1 次请求，显著加速）
            </label>
            <button
              type="button"
              onClick={doPull}
              disabled={running}
              className="inline-flex items-center gap-1.5 h-8 px-3 rounded-btn bg-accent text-white text-xs hover:opacity-90 disabled:opacity-50"
            >
              <RefreshCw size={14} className={running ? 'animate-spin' : ''} />
              {running ? '同步中…' : '更新诊股快照'}
            </button>
          </div>
        </div>
        {running && (
          <p className="mt-2 text-xs text-accent flex items-center gap-1.5">
            <Loader2 size={12} className="animate-spin" />
            同步中 {progress?.done ?? 0}/{progress?.total ?? '…'} · 成功 {progress?.ok ?? 0} · 失败 {progress?.failed ?? 0}
          </p>
        )}
        {notice && <p className="mt-2 text-xs text-warning">{notice}</p>}
      </div>

      {/* 表格工具条 */}
      {total > 0 && (
        <div className="rounded-card bg-surface border border-border px-4 py-2.5 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-btn bg-elevated p-0.5">
              {(
                [
                  ['flat', '平铺'],
                  ['industry', '按行业分组'],
                  ['concept', '按概念分组'],
                ] as const
              ).map(([v, label]) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => {
                    setViewMode(v)
                    if (v === 'industry' && selectedIndustry === null && industries.length)
                      setSelectedIndustry(industries[0].name)
                    if (v === 'concept' && selectedConcept === null && concepts.length)
                      setSelectedConcept(concepts[0].name)
                  }}
                  className={`h-7 px-3 rounded-[6px] text-xs transition-colors ${
                    viewMode === v ? 'bg-accent text-white' : 'text-secondary hover:text-foreground'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <button type="button" onClick={resetChips} className="text-xs text-muted hover:text-foreground">
              清除筛选
            </button>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              type="button"
              onClick={() => setChipFund((v) => !v)}
              className={`h-6 px-2.5 rounded-full text-xs ${chipFund ? 'bg-accent text-white' : 'bg-elevated text-secondary'}`}
            >
              资金转强
            </button>
            <button
              type="button"
              onClick={() => setChipFin((v) => !v)}
              className={`h-6 px-2.5 rounded-full text-xs ${chipFin ? 'bg-accent text-white' : 'bg-elevated text-secondary'}`}
            >
              财务同比改善
            </button>
            <span className="inline-flex rounded-full bg-elevated p-0.5">
              {(
                [
                  ['all', '全部'],
                  ['non-st', '非 ST'],
                  ['st', '仅 ST'],
                ] as const
              ).map(([v, label]) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setStFilter(v)}
                  title="按 ST 风险警示状态筛选（口径：名称含 ST，含 *ST）"
                  className={`h-6 px-2.5 rounded-full text-xs transition-colors ${
                    stFilter === v ? 'bg-accent text-white' : 'text-secondary hover:text-foreground'
                  }`}
                >
                  {label}
                </button>
              ))}
            </span>
          </div>
        </div>
      )}

      {/* 内容区 */}
      {total === 0 ? (
        <div className="rounded-card bg-surface border border-border px-6 py-14 text-center">
          <p className="text-sm text-muted">还没有诊股快照数据</p>
          <p className="text-xs text-muted mt-1">
            点击「更新诊股快照」对 A 股全量拉取评分（耗时较长，切走页面不影响同步，左侧菜单可见进度）
          </p>
        </div>
      ) : (
        <div className={`grid gap-4 ${viewMode !== 'flat' ? 'lg:grid-cols-[260px_1fr]' : ''}`}>
        {viewMode !== 'flat' && (
          <aside className="flex max-h-[60vh] min-w-0 flex-col rounded-2xl border border-border bg-surface p-2.5">
            <div className="shrink-0 px-1 pb-2.5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-foreground">
                  {viewMode === 'industry' ? '行业矩阵' : '概念矩阵'}
                </h3>
                <span className="text-[10px] text-muted">
                  Top {(viewMode === 'industry' ? shownIndustries : shownConcepts).length}
                </span>
              </div>
              <div className="mt-2 relative">
                <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                <input
                  value={groupSearch}
                  onChange={(e) => setGroupSearch(e.target.value)}
                  placeholder={viewMode === 'industry' ? '搜索行业' : '搜索概念'}
                  className="h-8 w-full rounded-lg border border-border bg-base pl-8 pr-3 text-xs text-foreground outline-none focus:border-accent/50"
                />
              </div>
              <div className="mt-2 grid grid-cols-4 overflow-hidden rounded-lg border border-border text-[10px]">
                {(
                  [
                    ['avg', '均分'],
                    ['fund', '资金'],
                    ['tech', '技术'],
                    ['finance', '财务'],
                  ] as [MatrixSortKey, string][]
                ).map(([k, label]) => (
                  <button
                    key={k}
                    type="button"
                    onClick={() => setMatrixSort(k)}
                    className={`py-1.5 transition-colors ${matrixSort === k ? 'bg-accent/15 text-accent' : 'bg-base text-muted hover:text-foreground'}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <div className="max-h-[52vh] overflow-auto rounded-lg border border-border/50">
              {(viewMode === 'industry' ? shownIndustries : shownConcepts).length === 0 ? (
                <p className="px-2.5 py-4 text-center text-xs text-muted">
                  {viewMode === 'concept' && concepts.length === 0
                    ? '暂无概念数据，请先在「扩展数据-概念」获取 ext_gn_ths'
                    : '无匹配分组'}
                </p>
              ) : (
                (viewMode === 'industry' ? shownIndustries : shownConcepts).map((g) => (
                  <button
                    key={g.name}
                    type="button"
                    onClick={() =>
                      viewMode === 'industry' ? setSelectedIndustry(g.name) : setSelectedConcept(g.name)
                    }
                    className={`w-full border-b border-border/50 px-2.5 py-2 text-left transition-colors last:border-b-0 ${
                      (viewMode === 'industry' ? selectedIndustry : selectedConcept) === g.name
                        ? 'bg-accent/10'
                        : 'hover:bg-elevated/40'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="min-w-0 flex-1 truncate text-xs font-medium text-foreground">{g.name}</span>
                      <span className="font-mono text-xs text-foreground">{fmt(g.avg)}</span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[10px] text-muted">
                      <span>{g.count}只</span>
                      <span className="ml-auto">均分 {fmt(g.avg)}</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </aside>
        )}
          <div className="rounded-card bg-surface border border-border overflow-hidden">
            <div className="overflow-auto max-h-[60vh]">
              <table ref={tableRef} className="w-full border-collapse text-sm">
                <thead className="sticky top-0 bg-surface z-10">
                  <tr className="border-b border-border">
                    <th className="px-2 py-1.5 text-left text-xs font-medium text-muted">名称 / 代码</th>
                    {viewMode === 'flat' ? (
                      <th className="px-2 py-1.5 text-left text-xs font-medium text-muted">行业</th>
                    ) : null}
                    {SORT_COLS.map((c) => (
                      <HeaderCol key={c.key} col={c} sortKey={sortKey} sortDir={sortDir} onSort={onSort} right>
                        {c.label}
                      </HeaderCol>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {virtualized ? (
                    <>
                      {topPadding > 0 && (
                        <tr aria-hidden="true">
                          <td colSpan={12} className="p-0 border-0" style={{ height: topPadding }} />
                        </tr>
                      )}
                      {virtualRows.map((v) => renderBodyRow(viewRows[v.index], v.index))}
                      {bottomPadding > 0 && (
                        <tr aria-hidden="true">
                          <td colSpan={12} className="p-0 border-0" style={{ height: bottomPadding }} />
                        </tr>
                      )}
                    </>
                  ) : (
                    viewRows.map((r, i) => renderBodyRow(r, i))
                  )}
                  {viewRows.length === 0 && (
                    <tr>
                      <td colSpan={12} className="px-3 py-10 text-center text-xs text-muted">
                        无符合条件的数据
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <p className="px-3 py-1.5 text-[11px] text-muted border-t border-border">
              显示 {viewRows.length} / 快照 {filtered.length} 只 · 点击行查看完整诊股详情（实时拉取单只，不落盘）
            </p>
          </div>
        </div>
      )}

      {selected && (
        <DiagnoseDetailDialog symbol={selected.symbol} name={selected.name} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}
