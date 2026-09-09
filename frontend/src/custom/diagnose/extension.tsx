import type { ComponentType } from 'react'
import { Radar } from 'lucide-react'
import type { FrontendExtension, FrontendSlotContextMap } from '@/extensions/types'

import DiagnosePage from './DiagnosePage'
import FooterSummary from './FooterSummary'
import SyncStatusNav from './SyncStatusNav'

// 插槽注册表以「全部插槽上下文并集」作为组件类型约束（见 extensions/types.ts），
// 实际渲染时只透传本插槽上下文，这里做一次显式类型收窄。
type SlotContextAll = FrontendSlotContextMap[keyof FrontendSlotContextMap]

const extension: FrontendExtension = {
  id: 'ths.diagnose',
  apiVersion: 1,
  routes: [{ id: 'ths-diagnose', path: '/diagnose', component: DiagnosePage }],
  navigation: [
    { id: 'ths-diagnose', routeId: 'ths-diagnose', label: '智能诊股', icon: Radar, order: 400 },
  ],
  slots: [
    {
      name: 'stock-preview.footer',
      id: 'ths-diagnose-footer-summary',
      order: 100,
      component: FooterSummary as unknown as ComponentType<SlotContextAll>,
    },
    {
      name: 'layout.navigation.extra',
      id: 'ths-diagnose-sync-status',
      order: 10,
      component: SyncStatusNav as unknown as ComponentType<SlotContextAll>,
    },
  ],
}

export default extension
