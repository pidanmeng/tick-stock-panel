import { useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api'
import { QK } from '@/lib/queryKeys'

/**
 * 诊股快照同步进度的全局查询。
 * 只要服务端任务 running，就以 1.5s 间隔轮询；结束自动停。
 * 页面与左侧菜单共用同一 queryKey（TanStack Query 全局缓存），
 * 因此切换路由后状态不丢、回页面立即取到最新。
 */
export function useDiagnoseProgress() {
  return useQuery({
    queryKey: QK.diagnoseProgress,
    queryFn: () => api.thsDiagnoseProgress(),
    refetchInterval: (query) => {
      const data = query.state.data
      return data && data.running ? 1500 : false
    },
  })
}
