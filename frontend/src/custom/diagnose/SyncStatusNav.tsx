import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'

import { useDiagnoseProgress } from './useDiagnoseProgress'

/**
 * 左侧菜单栏的诊股同步状态条（layout.navigation.extra 插槽）。
 * Layout 常驻挂载，切到其它页面仍可见；点击回到 /diagnose。
 */
export default function SyncStatusNav({ collapsed }: { collapsed: boolean; pathname: string }) {
  const navigate = useNavigate()
  const { data } = useDiagnoseProgress()

  if (!data?.running) return null

  return (
    <button
      type="button"
      onClick={() => navigate('/diagnose')}
      title="智能诊股同步中"
      className={`w-full flex items-center gap-2 px-3 py-1.5 rounded-btn bg-elevated text-accent hover:bg-elevated/80 transition-colors duration-150 ease-smooth ${
        collapsed ? 'justify-center' : 'justify-start'
      }`}
    >
      <Loader2 size={13} className="shrink-0 animate-spin" />
      {!collapsed && (
        <span className="text-xs leading-none">
          诊股同步 {data.done}/{data.total || '…'}
        </span>
      )}
    </button>
  )
}
