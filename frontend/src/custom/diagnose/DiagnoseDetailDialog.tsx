import { useEffect, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { X, Loader2 } from 'lucide-react'
import type { EChartsOption } from 'echarts'

import { api } from '@/lib/api'
import { QK } from '@/lib/queryKeys'
import { useChartTheme } from '@/lib/theme'
import type { DiagnoseSummarySection } from '@/lib/api'
import { EChart } from './EChart'

type Any = Record<string, unknown>

const num = (v: unknown): number | null =>
  typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : null
const fmt = (v: unknown, d = 2): string => {
  const n = num(v)
  return n === null || Number.isNaN(n) ? '—' : n.toFixed(d)
}

// 画布调色板（与主题无关的固定语义色；轴文字用 theme.text）
const ACCENT = '#3B82F6'
const COMP = '#F59E0B'
const NEUTRAL = '#A1A1AA'

const ABIL_IDS = ['profit', 'growth', 'operate', 'cash', 'pay', 'asset_quality'] as const
const ABIL_NAMES = ['盈利能力', '成长能力', '营运能力', '现金流', '偿债能力', '资产质量']

function Section({
  title,
  loading,
  error,
  children,
}: {
  title: string
  loading?: boolean
  error?: boolean
  children: ReactNode
}) {
  return (
    <div className="rounded-card bg-surface border border-border px-4 py-3">
      <h3 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
        {title}
        {loading && <Loader2 size={13} className="animate-spin text-muted" />}
        {error && <span className="text-xs font-normal text-warning">获取失败</span>}
      </h3>
      {children}
    </div>
  )
}

/** 分段切换 chips（单选组）。 */
function Chips<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div className="inline-flex flex-wrap items-center gap-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`h-6 px-2 rounded-full text-xs transition-colors ${
            value === o.value ? 'bg-accent text-white' : 'bg-elevated text-secondary hover:text-foreground'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

/* ============ 详情弹窗 ============ */
export default function DiagnoseDetailDialog({
  symbol,
  name,
  onClose,
}: {
  symbol: string
  name?: string | null
  onClose: () => void
}) {
  const theme = useChartTheme()
  const [fundWin, setFundWin] = useState<'one-month' | 'one-year'>('one-month')
  const [valIdx, setValIdx] = useState<'pb' | 'pe' | 'pof' | 'ps'>('pb')
  const [valPeriod, setValPeriod] = useState<'1' | '3' | '5' | '10'>('1')

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const summaryQ = useQuery({
    queryKey: QK.diagnoseStock(`${symbol}:summary`),
    queryFn: () => api.thsDiagnoseStockSummary(symbol),
    retry: 1,
  })
  const financeQ = useQuery({
    queryKey: QK.diagnoseStock(`${symbol}:finance`),
    queryFn: () => api.thsDiagnoseStockFinance(symbol),
    retry: 1,
  })
  const fundQ = useQuery({
    queryKey: QK.diagnoseStock(`${symbol}:fund:${fundWin}`),
    queryFn: () => api.thsDiagnoseStockFund(symbol, fundWin),
    retry: 1,
  })
  const valuationQ = useQuery({
    queryKey: QK.diagnoseStock(`${symbol}:valuation:${valIdx}:${valPeriod}`),
    queryFn: () => api.thsDiagnoseStockValuation(symbol, valIdx, valPeriod),
    retry: 1,
  })
  const messageQ = useQuery({
    queryKey: QK.diagnoseStock(`${symbol}:message`),
    queryFn: () => api.thsDiagnoseStockMessage(symbol),
    retry: 1,
  })

  const summary = summaryQ.data as DiagnoseSummarySection | undefined
  const scores = summary?.scores ?? {}
  const finance = financeQ.data as Any | undefined
  const fund = fundQ.data as Any | undefined
  const valuation = valuationQ.data as Any | undefined
  const message = messageQ.data as Any | undefined

  const abilities = Array.isArray(finance?.abilities) ? (finance?.abilities as Any[]) : []
  const highlights = Array.isArray(finance?.highlight) ? (finance?.highlight as Any[]) : []
  const risks = Array.isArray(finance?.risk) ? (finance?.risk as Any[]) : []
  const fundRows = Array.isArray(fund?.history) ? (fund?.history as Any[]) : []
  const valPoints = Array.isArray(valuation?.points) ? (valuation?.points as Any[]) : []
  const msgRows = Array.isArray(message?.rows) ? (message?.rows as Any[]) : []

  // ---------- 财务六维雷达（当期 vs 上年同期） ----------
  const abVal = (id: string, field: 'current' | 'last'): number => {
    const a = abilities.find((x) => x.id === id)
    if (!a) return 0
    return num(a[field]) ?? 0
  }
  const curVals = ABIL_IDS.map((id) => abVal(id, 'current'))
  const lastVals = ABIL_IDS.map((id) => abVal(id, 'last'))
  const hasRadar = curVals.some((v) => v > 0) || lastVals.some((v) => v > 0)
  const financeRadarOpt: EChartsOption = {
    legend: {
      top: 0,
      data: ['当期', '上年同期'],
      textStyle: { color: theme.text, fontSize: 11 },
      itemWidth: 14,
    },
    radar: {
      center: ['50%', '58%'],
      radius: '62%',
      indicator: ABIL_NAMES.map((nm) => ({ name: nm, max: 5 })),
      axisName: { color: theme.text, fontSize: 10 },
      splitLine: { lineStyle: { color: theme.grid } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: theme.grid } },
    },
    series: [
      {
        type: 'radar',
        symbolSize: 3,
        data: [
          {
            name: '当期',
            value: curVals,
            itemStyle: { color: ACCENT },
            areaStyle: { color: ACCENT, opacity: 0.12 },
          },
          {
            name: '上年同期',
            value: lastVals,
            itemStyle: { color: COMP },
            areaStyle: { color: COMP, opacity: 0.06 },
          },
        ],
      },
    ],
  }

  // ---------- 资金走势折线 ----------
  const fundX = fundRows.map((r) => String(r.date ?? '').slice(4))
  const fundY = fundRows.map((r) => num(r.fund_score))
  const fundOpt: EChartsOption = {
    tooltip: { trigger: 'axis', backgroundColor: theme.tooltipBg, borderColor: theme.tooltipBorder, textStyle: { color: theme.tooltipText, fontSize: 11 } },
    grid: { left: 34, right: 10, top: 18, bottom: 22 },
    xAxis: { type: 'category', data: fundX, boundaryGap: false, axisLine: { lineStyle: { color: theme.border } }, axisLabel: { color: theme.text, fontSize: 10, interval: Math.max(1, Math.floor(fundX.length / 8)) } },
    yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: theme.grid } }, axisLabel: { color: theme.text, fontSize: 10 } },
    series: [{ type: 'line', name: '资金分', smooth: true, showSymbol: false, data: fundY, lineStyle: { width: 2, color: ACCENT }, itemStyle: { color: ACCENT } }],
  }

  // ---------- 估值折线（个股 vs 行业）+ 分位 ----------
  const valX = valPoints.map((p) => String(p.date ?? '').slice(5))
  const valStock = valPoints.map((p) => num(p.stock))
  const valInd = valPoints.map((p) => num(p.industry))
  const lastPct = [...valPoints].reverse().find((p) => num(p.pct) !== null)
  const valOpt: EChartsOption = {
    tooltip: { trigger: 'axis', backgroundColor: theme.tooltipBg, borderColor: theme.tooltipBorder, textStyle: { color: theme.tooltipText, fontSize: 11 } },
    legend: { top: 0, data: ['个股', '行业'], textStyle: { color: theme.text, fontSize: 11 }, itemWidth: 14 },
    grid: { left: 40, right: 12, top: 26, bottom: 22 },
    xAxis: { type: 'category', data: valX, boundaryGap: false, axisLine: { lineStyle: { color: theme.border } }, axisLabel: { color: theme.text, fontSize: 10, interval: Math.max(1, Math.floor(valX.length / 8)) } },
    yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: theme.grid } }, axisLabel: { color: theme.text, fontSize: 10 } },
    series: [
      { type: 'line', name: '个股', smooth: true, showSymbol: false, data: valStock, lineStyle: { width: 2, color: ACCENT }, itemStyle: { color: ACCENT } },
      { type: 'line', name: '行业', smooth: true, showSymbol: false, data: valInd, lineStyle: { width: 1.5, color: NEUTRAL, type: 'dashed' }, itemStyle: { color: NEUTRAL } },
    ],
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto bg-base/80 backdrop-blur-sm p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-5xl rounded-dialog bg-surface border border-border mt-4 mb-8">
        <div className="flex items-start justify-between gap-3 border-b border-border px-5 py-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {name ?? summary?.name ?? symbol}
              <span className="ml-2 font-mono text-sm text-secondary">{symbol}</span>
            </h2>
            <p className="text-xs text-muted mt-0.5">
              {summary?.industry_name ?? '—'} · 行业排名 {fmt(summary?.industry_rank, 0)} · 市场{' '}
              {fmt(summary?.market_rank, 0)}/{fmt(summary?.market_stock_total, 0)} · 长线价值口径，手动更新
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="关闭" className="text-muted hover:text-foreground p-1 rounded-btn transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* 概览：六维分 + 亮点/风险（纵向） */}
          <Section title="概览 · 六维评分" loading={summaryQ.isLoading} error={summaryQ.isError}>
            <div className="grid sm:grid-cols-2 gap-3">
              {[
                ['score_fund', '资金'],
                ['score_tech', '技术'],
                ['score_valuation', '估值'],
                ['score_message', '消息'],
                ['score_finance', '财务'],
                ['score_average', '综合均'],
              ].map(([k, label]) => (
                <div key={k} className="rounded-btn bg-elevated px-3 py-1.5 flex items-center justify-between">
                  <span className="text-xs text-muted">{label}</span>
                  <span className="font-mono tabular-nums text-sm text-foreground">{fmt((scores as Any)[k])}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-muted leading-relaxed mt-3">
              {summary?.finance_overview ?? '—'}
              {summary?.message_effect ? ` · ${summary.message_effect}` : ''}
            </p>
            {/* 亮点 / 风险：纵向排列，缺一侧时只展示存在的一侧 */}
            {!financeQ.isLoading && (
              <div className="mt-3 space-y-3">
                {highlights.length > 0 && (
                  <div className="rounded-btn bg-elevated px-3 py-2">
                    <p className="text-xs font-medium text-bull mb-1.5">亮点</p>
                    <ul className="space-y-1.5">
                      {highlights.map((h, i) => (
                        <li key={i} className="text-xs text-secondary leading-relaxed flex gap-2">
                          <span className="text-bull shrink-0">•</span>
                          <span>{String(h.name ?? '')}：{String(h.comment ?? '')}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {risks.length > 0 && (
                  <div className="rounded-btn bg-elevated px-3 py-2">
                    <p className="text-xs font-medium text-bear mb-1.5">风险</p>
                    <ul className="space-y-1.5">
                      {risks.map((r, i) => (
                        <li key={i} className="text-xs text-secondary leading-relaxed flex gap-2">
                          <span className="text-bear shrink-0">•</span>
                          <span>{String(r.name ?? '')}：{String(r.comment ?? '')}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </Section>

          {/* 财务：六维雷达（当期 vs 上年同期） */}
          <Section title="财务 · 六能力评分（当期 vs 上年同期）" loading={financeQ.isLoading} error={financeQ.isError}>
            {!financeQ.isLoading && !financeQ.isError && (
              <div className="flex flex-wrap items-start gap-4">
                <div className="min-w-[150px] text-sm space-y-1.5 pt-2">
                  <p className="text-xs text-muted">财务总分</p>
                  <p className="font-mono tabular-nums text-foreground">{fmt(finance?.share)}</p>
                  <p className="text-xs text-muted">上年同期</p>
                  <p className="font-mono tabular-nums text-secondary">{fmt(finance?.last)}</p>
                  <p className="text-xs text-muted">定性</p>
                  <p className="text-sm text-foreground">{finance?.keyword ? String(finance.keyword) : '—'}</p>
                </div>
                <div className="flex-1 min-w-[260px]">
                  {hasRadar ? (
                    <EChart option={financeRadarOpt} height={230} />
                  ) : (
                    <p className="text-xs text-muted py-10 text-center">暂无六能力评分</p>
                  )}
                </div>
              </div>
            )}
          </Section>

          <div className="grid lg:grid-cols-2 gap-4">
            {/* 资金 */}
            <Section title="资金 · 评分走势" loading={fundQ.isLoading} error={fundQ.isError}>
              <div className="flex items-center justify-between flex-wrap gap-2 mb-1">
                <div className="flex items-center gap-3 text-sm">
                  <span>
                    资金分 <b className="font-mono tabular-nums text-foreground">{fmt(fund?.fund_score)}</b>
                  </span>
                  <span className="text-xs text-muted">
                    较昨日{' '}
                    <b className={`font-mono tabular-nums ${(num(fund?.fund_score_minus) ?? 0) >= 0 ? 'text-bull' : 'text-bear'}`}>
                      {fmt(fund?.fund_score_minus, 3)}
                    </b>
                  </span>
                </div>
                <Chips
                  options={[
                    { value: 'one-month', label: '近 1 月' },
                    { value: 'one-year', label: '近 1 年' },
                  ]}
                  value={fundWin}
                  onChange={setFundWin}
                />
              </div>
              {fundRows.length > 1 ? <EChart option={fundOpt} height={190} /> : <p className="text-xs text-muted py-8 text-center">暂无资金历史</p>}
            </Section>

            {/* 估值 */}
            <Section title="估值 · 个股 vs 行业" loading={valuationQ.isLoading} error={valuationQ.isError}>
              <div className="flex items-center justify-between flex-wrap gap-2 mb-1">
                <Chips
                  options={[
                    { value: 'pb', label: 'PB' },
                    { value: 'pe', label: 'PE' },
                    { value: 'pof', label: 'PCF' },
                    { value: 'ps', label: 'PS' },
                  ]}
                  value={valIdx}
                  onChange={setValIdx}
                />
                <Chips
                  options={[
                    { value: '1', label: '1年' },
                    { value: '3', label: '3年' },
                    { value: '5', label: '5年' },
                    { value: '10', label: '10年' },
                  ]}
                  value={valPeriod}
                  onChange={setValPeriod}
                />
              </div>
              <p className="text-xs text-muted mb-1">
                当前历史分位（越低越便宜）：<b className="font-mono tabular-nums text-foreground">{lastPct ? fmt(num(lastPct.pct), 3) : '—'}</b>
              </p>
              {valPoints.length > 1 ? <EChart option={valOpt} height={170} /> : <p className="text-xs text-muted py-8 text-center">暂无估值序列</p>}
            </Section>
          </div>

          {/* 消息/公告研报 */}
          <Section title="公告 / 研报要点" loading={messageQ.isLoading} error={messageQ.isError}>
            {msgRows.length === 0 && <p className="text-xs text-muted">暂无要点</p>}
            <ul className="space-y-1.5 max-h-56 overflow-y-auto">
              {msgRows.slice(0, 15).map((m, i) => {
                const url = typeof m.url === 'string' ? m.url : null
                return (
                  <li key={i} className="rounded-btn bg-elevated px-3 py-1.5 text-xs leading-relaxed">
                    <div className="flex items-center gap-2">
                      <span className="font-mono tabular-nums text-muted">{String(m.pub_date ?? '')}</span>
                      <span className="rounded-full bg-accent/15 text-accent px-1.5 py-px">{String(m.label_property ?? '')}</span>
                      <span className="text-muted">{String(m.carrier === 'research' ? '研报' : '公告')}</span>
                    </div>
                    <p className="text-secondary mt-0.5">{String(m.overview ?? m.abstract ?? '')}</p>
                    {url && (
                      <a href={url} target="_blank" rel="noreferrer" className="text-accent hover:underline">
                        查看原文
                      </a>
                    )}
                  </li>
                )
              })}
            </ul>
          </Section>
        </div>
      </div>
    </div>
  )
}
