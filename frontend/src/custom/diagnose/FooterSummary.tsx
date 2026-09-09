import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ScanSearch } from 'lucide-react'

import { api } from '@/lib/api'
import { QK } from '@/lib/queryKeys'

/**
 * 个股 K 线弹窗底部（stock-preview.footer 插槽）的智能诊股摘要入口。
 * 仅拉单只总评做紧凑展示；点击跳到 /diagnose?symbol=... 查看完整详情。
 */
export default function FooterSummary({
  symbol,
  name,
}: {
  symbol: string
  name: string | null
  view: 'daily' | 'intraday'
}) {
  const navigate = useNavigate()
  const { data, isLoading, isError } = useQuery({
    queryKey: QK.diagnoseStock(symbol),
    queryFn: () => api.thsDiagnoseStockSummary(symbol),
    enabled: Boolean(symbol),
    retry: 1,
  })

  const scores = data?.scores ?? {}
  const dims: { key: string; label: string }[] = [
    { key: 'score_fund', label: '资金' },
    { key: 'score_tech', label: '技术' },
    { key: 'score_valuation', label: '估值' },
    { key: 'score_finance', label: '财务' },
  ]
  const avg = scores.score_average

  return (
    <div className="border-t border-border px-4 py-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">智能诊股</span>
          {isLoading && <span className="text-xs text-muted">加载评分…</span>}
          {isError && <span className="text-xs text-warning">评分获取失败（私有接口可能不可用）</span>}
          {!isLoading && !isError && (
            <>
              {dims.map((d) => (
                <span key={d.key} className="flex items-center gap-1 text-xs">
                  <span className="text-muted">{d.label}</span>
                  <span className="font-mono tabular-nums">
                    {(scores as Record<string, number | null | undefined>)[d.key]?.toFixed(1) ?? '—'}
                  </span>
                </span>
              ))}
              <span className="flex items-center gap-1 text-xs">
                <span className="text-muted">均</span>
                <span className="font-mono tabular-nums">{avg?.toFixed(2) ?? '—'}</span>
              </span>
            </>
          )}
        </div>
        <button
          type="button"
          onClick={() => navigate(`/diagnose?symbol=${encodeURIComponent(symbol)}`)}
          className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-btn bg-elevated text-xs text-secondary hover:bg-elevated/80 hover:text-foreground transition-colors duration-150 ease-smooth"
        >
          <ScanSearch size={14} />
          完整诊股 {name ?? ''}
        </button>
      </div>
    </div>
  )
}
