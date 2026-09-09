import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'
import { useChartTheme } from '@/lib/theme'

/**
 * 轻量 ECharts 容器：自动 init / resize / dispose，option 变化时全量替换。
 * 主题色经 useChartTheme 取画布调色板（不吃 CSS 变量）。
 */
export function EChart({
  option,
  height = 200,
  className = '',
}: {
  option: EChartsOption | null
  height?: number
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const theme = useChartTheme()

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const chart = echarts.init(el, undefined, { renderer: 'canvas' })
    const ro = new ResizeObserver(() => chart.resize())
    ro.observe(el)
    return () => {
      ro.disconnect()
      chart.dispose()
    }
  }, [])

  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.getInstanceByDom(ref.current)
    if (!chart || !option) return
    chart.setOption(option, { notMerge: true })
  }, [option, theme])

  return <div ref={ref} className={className} style={{ height, width: '100%' }} />
}
