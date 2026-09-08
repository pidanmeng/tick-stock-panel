import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Eye, EyeOff, ExternalLink, GripVertical, Settings, Bell, Plus, Pencil, Trash2, RotateCcw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Modal } from '@/components/Modal'
import { api, type NavLayoutItem } from '@/lib/api'
import { QK } from '@/lib/queryKeys'
import { usePreferences } from '@/lib/useSharedQueries'

interface NavEntry {
  id: string
  label: string
  type: 'builtin' | 'analysis'
  visible: boolean
}

// 与 Layout 侧边栏默认顺序保持一致 (nav_order 未保存时的默认展示顺序)
const BUILTIN_PAGES: NavEntry[] = [
  { id: '/', label: '看板', type: 'builtin', visible: true },
  { id: '/watchlist', label: '自选', type: 'builtin', visible: true },
  { id: '/screener', label: '策略', type: 'builtin', visible: true },
  { id: '/factors', label: '因子', type: 'builtin', visible: true },
  { id: '/backtest', label: '回测', type: 'builtin', visible: true },
  { id: '/stock-analysis', label: '个股分析', type: 'builtin', visible: true },
  { id: '/limit-ladder', label: '连板梯队', type: 'builtin', visible: true },
  { id: '/concept-analysis', label: '概念分析', type: 'builtin', visible: true },
  { id: '/industry-analysis', label: '行业分析', type: 'builtin', visible: true },
  { id: '/financials', label: '财务分析', type: 'builtin', visible: true },
  { id: '/monitor', label: '监控中心', type: 'builtin', visible: true },
  { id: '/regime', label: '市场环境', type: 'builtin', visible: true },
  { id: '/abnormal', label: '异动监控', type: 'builtin', visible: true },
  { id: '/lots', label: '持仓提醒', type: 'builtin', visible: true },
  { id: '/signals', label: '信号库', type: 'builtin', visible: true },
  { id: '/review', label: '复盘', type: 'builtin', visible: true },
  { id: '/indices', label: '指数', type: 'builtin', visible: true },
  { id: '/data', label: '数据', type: 'builtin', visible: true },
]

// ── Sortable row ──

function SortableItem({ entry, hidden, onToggleHidden, badgeEnabled, onToggleBadge }: {
  entry: NavEntry
  hidden: boolean
  onToggleHidden: (id: string) => void
  badgeEnabled?: boolean
  onToggleBadge?: (id: string) => void
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: entry.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
    zIndex: isDragging ? 10 : undefined,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`grid grid-cols-[2.5rem_1fr_4.5rem_3rem_3rem_3rem] items-center border-b border-border/70 px-4 py-3 last:border-b-0 ${
        isDragging ? 'bg-elevated rounded-lg shadow-lg' : ''
      } ${hidden ? 'opacity-50' : ''}`}
    >
      <div
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-muted hover:text-foreground transition-colors"
      >
        <GripVertical className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex items-center gap-2">
        <span className={`truncate text-sm font-medium ${!hidden ? 'text-foreground' : 'text-muted line-through'}`}>
          {entry.label}
        </span>
        {hidden && (
          <span className="rounded bg-elevated px-1.5 py-0.5 text-[10px] text-muted shrink-0">已隐藏</span>
        )}
        <span className="truncate text-[11px] text-muted font-mono">{entry.id}</span>
      </div>
      <div>
        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] ${
          entry.type === 'analysis' ? 'bg-accent/10 text-accent' : 'bg-elevated text-muted'
        }`}>
          {entry.type === 'builtin' ? '内置' : '扩展'}
        </span>
      </div>
      <div className="flex justify-center">
        <button
          onClick={() => onToggleHidden(entry.id)}
          className={`rounded p-1 transition-colors ${
            hidden
              ? 'text-muted hover:text-accent hover:bg-accent/10'
              : 'text-accent hover:bg-accent/10'
          }`}
          title={hidden ? '显示' : '隐藏'}
        >
          {hidden ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
      <div className="flex justify-center">
        {entry.type === 'builtin' ? (
          <Link
            to={entry.id}
            className="rounded p-1 text-muted hover:text-accent hover:bg-accent/10 transition-colors"
            title="打开页面"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        ) : (
          <Link
            to={`/settings?tab=ext-pages`}
            className="rounded p-1 text-muted hover:text-accent hover:bg-accent/10 transition-colors"
            title="编辑扩展页面"
          >
            <Settings className="h-3.5 w-3.5" />
          </Link>
        )}
      </div>
      {/* 第 6 列: 徽标开关 (仅监控中心) */}
      <div className="flex justify-center">
        {onToggleBadge && (
          <button
            onClick={() => onToggleBadge(entry.id)}
            className={`rounded p-1 transition-colors ${
              badgeEnabled
                ? 'text-accent hover:bg-accent/10'
                : 'text-muted hover:text-accent hover:bg-accent/10'
            }`}
            title={badgeEnabled ? '关闭数字提示' : '开启数字提示'}
          >
            <Bell className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  )
}

// ── Main panel ──

export function SettingsMenuSettingsPanel() {
  const qc = useQueryClient()
  const { data: prefs } = usePreferences()
  const menus = useQuery({ queryKey: QK.analysisMenus, queryFn: api.analysisMenus })

  const analysisEntries: NavEntry[] = (menus.data?.items ?? []).map(m => ({
    id: m.id,
    label: m.label,
    type: 'analysis' as const,
    visible: m.visible,
  }))

  // 布局列表: 后端返回含默认布局 (id='') 的完整列表; 旧后端无字段时兜底为默认布局。
  const layouts = useMemo<NavLayoutItem[]>(() => {
    const src = prefs?.nav_layouts ?? []
    if (src.length > 0) return src
    return [{
      id: '',
      name: '默认布局',
      nav_order: prefs?.nav_order ?? [],
      nav_hidden: prefs?.nav_hidden ?? [],
    }]
  }, [prefs?.nav_layouts, prefs?.nav_order, prefs?.nav_hidden])

  const activeLayoutId = prefs?.nav_active_layout ?? ''

  // 面板当前编辑的布局 (独立于生效布局; '' = 默认布局)
  const [editLayoutId, setEditLayoutId] = useState('')
  const editing = useMemo(
    () => layouts.find(it => it.id === editLayoutId) ?? layouts[0],
    [layouts, editLayoutId],
  )

  // 拖拽过程的乐观顺序 — 切换编辑布局时必须清空, 避免残留上一个布局的顺序
  const [localOrder, setLocalOrder] = useState<string[] | null>(null)
  useEffect(() => { setLocalOrder(null) }, [editLayoutId])

  // 编辑目标被删除或偏好数据未就绪时回退默认布局
  useEffect(() => {
    if (!layouts.some(it => it.id === editLayoutId)) setEditLayoutId('')
  }, [layouts, editLayoutId])

  const editOrder = editing?.nav_order ?? []
  const editHidden = editing?.nav_hidden ?? []
  const editLayoutIdStr = editing?.id ?? ''

  const allEntries = useMemo(() => {
    const saved = editOrder
    const entryMap = new Map<string, NavEntry>()
    for (const e of BUILTIN_PAGES) entryMap.set(e.id, e)
    for (const e of analysisEntries) entryMap.set(e.id, e)

    if (saved.length === 0) return [...BUILTIN_PAGES, ...analysisEntries]

    const ordered: NavEntry[] = []
    const seen = new Set<string>()
    for (const id of saved) {
      const entry = entryMap.get(id)
      if (entry) {
        ordered.push(entry)
        seen.add(id)
      }
    }
    for (const e of [...BUILTIN_PAGES, ...analysisEntries]) {
      if (seen.has(e.id)) continue
      // 未保存过排序的新条目: 内置页插回默认位置, 分析菜单追加到末尾
      const defaultIndex = BUILTIN_PAGES.findIndex(p => p.id === e.id)
      let anchor = -1
      if (defaultIndex > 0) {
        for (let i = defaultIndex - 1; i >= 0 && anchor < 0; i -= 1) {
          anchor = ordered.findIndex(o => o.id === BUILTIN_PAGES[i].id)
        }
      }
      if (anchor >= 0) ordered.splice(anchor + 1, 0, e)
      else if (defaultIndex >= 0) ordered.unshift(e)
      else ordered.push(e)
    }
    return ordered
  }, [editOrder, analysisEntries])

  const hiddenSet = useMemo(() => new Set(editHidden), [editHidden])

  const orderedEntries = useMemo(() => {
    const order = localOrder ?? editOrder
    if (!order.length) return allEntries
    const byId = new Map(allEntries.map(e => [e.id, e]))
    const result: NavEntry[] = []
    const seen = new Set<string>()
    for (const id of order) {
      const e = byId.get(id)
      if (e) { result.push(e); seen.add(id) }
    }
    for (const e of allEntries) {
      if (seen.has(e.id)) continue
      // 与 allEntries 同一语义: 未保存的新内置页插回默认位置而非追加到末尾
      const defaultIndex = BUILTIN_PAGES.findIndex(p => p.id === e.id)
      let anchor = -1
      if (defaultIndex > 0) {
        for (let i = defaultIndex - 1; i >= 0 && anchor < 0; i -= 1) {
          anchor = result.findIndex(o => o.id === BUILTIN_PAGES[i].id)
        }
      }
      if (anchor >= 0) result.splice(anchor + 1, 0, e)
      else if (defaultIndex >= 0) result.unshift(e)
      else result.push(e)
    }
    return result
  }, [localOrder, editOrder, allEntries])

  const saveNavOrder = useMutation({
    mutationFn: (order: string[]) => api.saveNavOrder(order, editLayoutIdStr),
    onSuccess: () => {
      setLocalOrder(null)
      qc.invalidateQueries({ queryKey: QK.preferences })
    },
  })

  const saveNavHidden = useMutation({
    mutationFn: (hidden: string[]) => api.saveNavHidden(hidden, editLayoutIdStr),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.preferences }),
  })

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const ids = orderedEntries.map(e => e.id)
    const oldIdx = ids.indexOf(active.id as string)
    const newIdx = ids.indexOf(over.id as string)
    const reordered = arrayMove(ids, oldIdx, newIdx)
    setLocalOrder(reordered)
    saveNavOrder.mutate(reordered)
  }

  const toggleHidden = (id: string) => {
    const next = new Set(hiddenSet)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    saveNavHidden.mutate([...next])
  }

  // 监控中心徽标开关 (localStorage, 全局偏好, 不随布局保存)
  const [badgeEnabled, setBadgeEnabled] = useState(() => {
    try { return localStorage.getItem('monitor_badge_enabled') !== '0' } catch { return true }
  })
  const toggleBadge = (id: string) => {
    if (id !== '/monitor') return
    const next = !badgeEnabled
    setBadgeEnabled(next)
    try { localStorage.setItem('monitor_badge_enabled', next ? '1' : '0') } catch { /* ignore */ }
  }

  // 布局管理 (创建 / 重命名 / 重置 / 删除)
  const [layoutDialog, setLayoutDialog] = useState<null | 'create' | 'rename' | 'reset' | 'delete'>(null)
  const [layoutName, setLayoutName] = useState('')

  // 新建布局以「面板当前编辑的布局」为起点 (拷贝其排序/显隐)
  const createLayout = useMutation({
    mutationFn: (name: string) => api.createNavLayout(name, editLayoutIdStr),
    onSuccess: (res) => {
      setLayoutDialog(null)
      setEditLayoutId(res.layout.id)
      qc.invalidateQueries({ queryKey: QK.preferences })
    },
  })

  const renameLayout = useMutation({
    mutationFn: (name: string) => api.renameNavLayout(editLayoutIdStr, name),
    onSuccess: () => {
      setLayoutDialog(null)
      qc.invalidateQueries({ queryKey: QK.preferences })
    },
  })

  // 重置当前编辑布局: 清空自定义排序与显隐, 恢复默认菜单顺序 (全部显示)
  const canResetLayout = editOrder.length > 0 || editHidden.length > 0
  const resetLayout = useMutation({
    mutationFn: async () => {
      await api.saveNavOrder([], editLayoutIdStr)
      await api.saveNavHidden([], editLayoutIdStr)
    },
    onSuccess: () => {
      setLayoutDialog(null)
      setLocalOrder(null)
      qc.invalidateQueries({ queryKey: QK.preferences })
    },
  })

  const deleteLayout = useMutation({
    mutationFn: () => api.deleteNavLayout(editLayoutIdStr),
    onSuccess: () => {
      setLayoutDialog(null)
      setEditLayoutId('')
      qc.invalidateQueries({ queryKey: QK.preferences })
    },
  })

  const isEditingNamed = editLayoutIdStr !== ''
  const layoutSubmitting = createLayout.isPending || renameLayout.isPending
  const activeLayoutName = layouts.find(it => it.id === activeLayoutId)?.name ?? '默认布局'

  const openCreate = () => { setLayoutName(''); setLayoutDialog('create') }
  const openRename = () => { setLayoutName(editing?.name ?? ''); setLayoutDialog('rename') }

  return (
    <div className="max-w-5xl space-y-6">
      <section className="rounded-2xl border border-border bg-surface p-6 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.12),transparent_38%)]">
        <div className="text-[11px] uppercase tracking-[0.2em] text-accent/80">菜单设置</div>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">调整左侧菜单顺序</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-secondary">
          支持维护多套独立布局，每套布局各自保存菜单的排序与显隐。编辑与生效解耦：
          当前编辑「{editing?.name ?? '默认布局'}」，在页面底部状态栏切换生效布局。
          拖动左侧手柄排序，点击眼睛图标控制菜单在侧边栏中的显示或隐藏。
        </p>
      </section>

      {/* 布局方案管理 — 选择要编辑的布局 + 创建/重命名/删除 */}
      <section className="flex flex-wrap items-center gap-2 rounded-card border border-border bg-surface px-4 py-3">
        <label htmlFor="nav-layout-edit" className="shrink-0 text-xs font-medium text-secondary">编辑布局</label>
        <select
          id="nav-layout-edit"
          value={editLayoutIdStr}
          onChange={e => setEditLayoutId(e.target.value)}
          className="h-8 min-w-44 rounded border border-border bg-base px-2 text-xs text-foreground focus:outline-none focus:border-accent/50"
        >
          {layouts.map(it => (
            <option key={it.id} value={it.id}>
              {it.name}{it.id === activeLayoutId ? ' · 当前生效' : ''}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center gap-1 rounded-btn border border-accent/30 bg-accent/10 px-2.5 py-1.5 text-xs font-medium text-accent transition-colors hover:bg-accent/20"
        >
          <Plus className="h-3.5 w-3.5" /> 新建布局
        </button>
        <button
          type="button"
          onClick={() => setLayoutDialog('reset')}
          disabled={!canResetLayout}
          title="清空该布局的自定义排序与显隐, 恢复默认菜单顺序"
          className="inline-flex items-center gap-1 rounded-btn border border-border px-2.5 py-1.5 text-xs text-secondary transition-colors hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-40"
        >
          <RotateCcw className="h-3 w-3" /> 重置
        </button>
        {isEditingNamed && (
          <>
            <button
              type="button"
              onClick={openRename}
              className="inline-flex items-center gap-1 rounded-btn border border-border px-2.5 py-1.5 text-xs text-secondary transition-colors hover:bg-elevated"
            >
              <Pencil className="h-3 w-3" /> 重命名
            </button>
            <button
              type="button"
              onClick={() => setLayoutDialog('delete')}
              className="inline-flex items-center gap-1 rounded-btn border border-danger/30 bg-danger/10 px-2.5 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/20"
            >
              <Trash2 className="h-3 w-3" /> 删除
            </button>
          </>
        )}
        <span className="ml-auto hidden text-[11px] text-muted lg:inline">
          当前生效: {activeLayoutName} · 可在底部状态栏切换
        </span>
      </section>

      <section className="rounded-card border border-border bg-surface overflow-hidden">
        <div className="grid grid-cols-[2.5rem_1fr_4.5rem_3rem_3rem_3rem] items-center border-b border-border px-4 py-2 text-[11px] text-muted">
          <div />
          <div>菜单</div>
          <div>类型</div>
          <div className="text-center">显示</div>
          <div className="text-center">设置</div>
          <div className="text-center">数字</div>
        </div>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={orderedEntries.map(e => e.id)}
            strategy={verticalListSortingStrategy}
          >
            {orderedEntries.map((entry) => (
              <SortableItem
                key={entry.id}
                entry={entry}
                hidden={hiddenSet.has(entry.id)}
                onToggleHidden={toggleHidden}
                badgeEnabled={entry.id === '/monitor' ? badgeEnabled : undefined}
                onToggleBadge={entry.id === '/monitor' ? toggleBadge : undefined}
              />
            ))}
          </SortableContext>
        </DndContext>

        {menus.isLoading && (
          <div className="px-5 py-10 text-center text-sm text-muted">正在加载菜单...</div>
        )}
      </section>

      {/* 布局创建/重命名/重置/删除弹窗 */}
      {layoutDialog && (
        <Modal
          onClose={() => setLayoutDialog(null)}
          ariaLabel={
            layoutDialog === 'delete' ? '删除布局确认'
              : layoutDialog === 'reset' ? '重置布局确认'
                : layoutDialog === 'create' ? '新建布局'
                  : '重命名布局'
          }
        >
          {layoutDialog === 'delete' ? (
            <div className="p-5 space-y-4">
              <div className="text-sm font-semibold text-foreground">删除布局「{editing?.name}」?</div>
              <p className="text-xs leading-5 text-secondary">
                该布局保存的菜单排序与显隐配置将被删除。
                {editLayoutIdStr === activeLayoutId && ' 该布局当前正在生效, 删除后将自动切回默认布局。'}
                默认布局与其他布局不受影响。
              </p>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setLayoutDialog(null)}
                  className="rounded-btn border border-border px-3 py-1.5 text-xs text-secondary transition-colors hover:bg-elevated"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={() => deleteLayout.mutate()}
                  disabled={deleteLayout.isPending}
                  className="rounded-btn border border-danger/30 bg-danger/10 px-3 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {deleteLayout.isPending ? '删除中...' : '删除'}
                </button>
              </div>
            </div>
          ) : layoutDialog === 'reset' ? (
            <div className="p-5 space-y-4">
              <div className="text-sm font-semibold text-foreground">重置布局「{editing?.name}」?</div>
              <p className="text-xs leading-5 text-secondary">
                将清空该布局保存的自定义菜单排序与显隐，恢复为默认菜单顺序（全部显示）。
                默认布局与其他布局不受影响。
              </p>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setLayoutDialog(null)}
                  className="rounded-btn border border-border px-3 py-1.5 text-xs text-secondary transition-colors hover:bg-elevated"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={() => resetLayout.mutate()}
                  disabled={resetLayout.isPending}
                  className="rounded-btn border border-danger/30 bg-danger/10 px-3 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {resetLayout.isPending ? '重置中...' : '重置'}
                </button>
              </div>
            </div>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const name = layoutName.trim()
                if (!name || layoutSubmitting) return
                if (layoutDialog === 'create') createLayout.mutate(name)
                else if (layoutDialog === 'rename') renameLayout.mutate(name)
              }}
              className="p-5 space-y-4"
            >
              <div className="text-sm font-semibold text-foreground">
                {layoutDialog === 'create' ? '新建布局' : '重命名布局'}
              </div>
              {layoutDialog === 'create' && (
                <p className="text-xs leading-5 text-secondary">
                  初始内容将拷贝自当前编辑布局「{editing?.name ?? '默认布局'}」的排序与显隐，可在创建后继续调整。
                </p>
              )}
              <input
                autoFocus
                value={layoutName}
                onChange={e => setLayoutName(e.target.value)}
                maxLength={24}
                placeholder={layoutDialog === 'create' ? '布局名称，如：短线、价值投资' : '新名称'}
                className="h-9 w-full rounded-btn border border-border bg-base px-3 text-xs text-foreground focus:outline-none focus:border-accent/50"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setLayoutDialog(null)}
                  className="rounded-btn border border-border px-3 py-1.5 text-xs text-secondary transition-colors hover:bg-elevated"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={!layoutName.trim() || layoutSubmitting}
                  className="rounded-btn border border-accent/30 bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {layoutSubmitting ? '保存中...' : '确定'}
                </button>
              </div>
            </form>
          )}
        </Modal>
      )}
    </div>
  )
}
