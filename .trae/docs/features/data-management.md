# 功能文档：数据管理 Data

> 文档依据代码实际实现整理，所有引用标注 `路径:行号`。仅描述已实现能力，未确认处标注「待确认」。

## 1. 功能概述

数据管理是 TSP 的数据运维门户（菜单「数据」，路由 `/data`，前端 [Data.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Data.tsx)）。它把底层数据链路（同步 → 指标计算 → 落盘 → 视图）以「数据画像卡片 + 任务进度 + 配置弹窗」的形式暴露给用户，覆盖四类能力：

1. **数据画像与状态监控**：日K、enriched、指数/ETF、分钟K、财务、复权因子、维表等 11 类数据的行数/日期范围/存储占用，含容量告警（[data.py](file:///c:/Code/tick-stock-panel/backend/app/api/data.py)）。
2. **盘后管道与手动任务**：盘后自动管道（[daily_pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py)）按日运行；用户可手动触发「立即同步」、查看/取消任务（[pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/api/pipeline.py)）；另有前向扩展历史、按日期修复缺失、重建 enriched 三类独立任务。
3. **扩展数据管理**：用户自定义数据源（CSV/Excel 上传、JSON 写入、URL 定时拉取），落盘为独立 Parquet，可关联标的维度参与分析（[ext_data.py](file:///c:/Code/tick-stock-panel/backend/app/services/ext_data.py)）。
4. **数据治理**：清除全部数据、刷新内存缓存、查看表结构 Schema、修复代码格式、数据完整性自检与自动修复（[data_integrity.py](file:///c:/Code/tick-stock-panel/backend/app/services/data_integrity.py)）。

核心设计约束（红线）：不修改 DuckDB 内存视图结构、Parquet schema、API 契约与 `data/` 目录布局；股票/ETF/指数分开存储与路由；复权、时区、交易日口径严格对齐。

## 2. 文件清单

### 前端

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| [Data.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Data.tsx) | 1302 | 数据管理页：画像卡片、任务进度、扩展数据 CRUD、各类设置弹窗 |

### 后端 API

| 文件 | 行数 | 路由前缀 | 职责 |
| --- | --- | --- | --- |
| [data.py](file:///c:/Code/tick-stock-panel/backend/app/api/data.py) | 877 | `/api/data` | 数据画像查询、Schema、缓存失效、数据清除 |
| [pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/api/pipeline.py) | 114 | `/api/pipeline` | 管道触发、任务进度/列表/取消 |
| [ext_data.py](file:///c:/Code/tick-stock-panel/backend/app/api/ext_data.py) | 1271 | `/api/ext-data` | 扩展数据 CRUD、上传、定时拉取、Schema 发现 |

### 后端服务

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| [kline_sync.py](file:///c:/Code/tick-stock-panel/backend/app/services/kline_sync.py) | 1490 | 日K/分钟K/除权因子同步、实时行情覆写、盘中脉冲拉取 |
| [extend_history.py](file:///c:/Code/tick-stock-panel/backend/app/services/extend_history.py) | 227 | 前向扩展历史（独立于盘后管道） |
| [repair_daily.py](file:///c:/Code/tick-stock-panel/backend/app/services/repair_daily.py) | 57 | 按日期修正/补全日K（复用盘后管道） |
| [data_integrity.py](file:///c:/Code/tick-stock-panel/backend/app/services/data_integrity.py) | 402 | 停机缺口/盘中快照检测、自动修复任务 |
| [ext_data.py](file:///c:/Code/tick-stock-panel/backend/app/services/ext_data.py) | 749 | 扩展配置管理、CSV/Excel 解析、Parquet 存储 |
| [ext_presets.py](file:///c:/Code/tick-stock-panel/backend/app/services/ext_presets.py) | 281 | 内置概念/行业扩展预设（仅创建配置，不自动拉取） |
| [ext_pull.py](file:///c:/Code/tick-stock-panel/backend/app/services/ext_pull.py) | 529 | 扩展数据定时拉取引擎（PullScheduler） |
| [pipeline_jobs.py](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py) | 533 | 任务注册表 JobStore + 重任务互斥执行槽 |

### 定时任务

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| [daily_pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py) | 1263 | 盘后管道编排、调度器注册、定时复盘（AI） |

## 3. 业务逻辑

### 3.1 数据画像与状态（`/api/data`）

- **画像统计**：`GET /status` 汇总 daily/enriched/index/etf/minute/adj_factor/instruments/financials 各表统计 + 磁盘存储 + 调度配置 + indicator_ready（[data.py:46-69](file:///c:/Code/tick-stock-panel/backend/app/api/data.py#L46-L69) 待确认）。统计优化：日K/enriched 只读分区目录名取日期范围（零数据扫描），adj_factor 对齐日K日期范围，minute 从分区目录数交易日（[data.py](file:///c:/Code/tick-stock-panel/backend/app/api/data.py) 内 `_table_cache` TTL 30s/120s、`_storage_cache` TTL 60s）。
- **缓存失效**：`invalidate_data_cache(table)` 按表名精确失效，`POST /refresh-cache` 重建 Polars 内存缓存（[data.py](file:///c:/Code/tick-stock-panel/backend/app/api/data.py)）。
- **清除数据**：`POST /clear` 清空全部 Parquet（含 EnrichedPublication 保护机制），清除同步历史、alerts、Polars 缓存、DuckDB 视图（[data.py](file:///c:/Code/tick-stock-panel/backend/app/api/data.py) 内 clear 端点，`POST /api/data/clear`）。
- **Schema 查询**：`GET /schema/{table}` 返回字段名、类型、中文说明（优先 DuckDB DESCRIBE，回退静态定义）。

### 3.2 盘后管道（`/api/pipeline` + `daily_pipeline.py`）

- **触发与进度**：`POST /run` 异步触发，返回 `job_id`，单飞模式复用活跃任务；`GET /jobs/{job_id}` 轮询进度（每次轮询同时触发 `reap_stale` 卡死检测）；`POST /jobs/{job_id}/cancel` 协作式取消；`GET /jobs` 列出最近任务（[pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/api/pipeline.py)）。重任务在 `ThreadPoolExecutor(max_workers=2)` 隔离，管道运行时暂停实时行情。
- **管道阶段**（[daily_pipeline.py run_now](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py)）：
  - Step 0：同步个股维表 + 解析标的池（CN_Equity_A）
  - Step 1：日K同步（4 分支：`override_start_date` 强制 batch / 实时行情覆写 / batch 补齐缺口 / 首次拉 1 年）
  - Step 1.5：除权因子同步（范围与日K拉取方式对齐）
  - Step 2：enriched 计算（全量/增量/受除权影响重算）+ 异常分区修复
  - Step 2.3：指数/ETF 同步（物理分开存储，ETF 可复权）
  - Step 2.5：分钟K同步（可选，按配置天数）
  - Step 2.6/2.7：市场环境(regime)与市场主线增量计算（默认关闭）
  - Step 3：刷新 DuckDB 视图
  - 完整性自愈：`scan_recent_integrity` 检测盘中快照/缺口，自动降级到范围拉取（[data_integrity.py](file:///c:/Code/tick-stock-panel/backend/app/services/data_integrity.py)）
  - `PipelineStageError`：阶段软失败累积，末尾抛出让任务标记为 failed 而非误报成功
- **调度器**：`start_scheduler()` 注册盘前 09:10 维表、盘后 15:35 管道、depth_finalize 15:02、能力重探 60min、定时复盘；节假日按交易日探针自动停轮询（[daily_pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py)）。
- **定时复盘（AI）**：`_run_scheduled_review` 流式生成复盘报告，推 SSE、落盘归档、推飞书/企微/邮件（[daily_pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py) 尾部，待确认精确行号）。

### 3.3 任务体系（`pipeline_jobs.py`）

- **JobStore**：每个 job 独立 JSON 文件（`data/job_store/{id}.json`），最多保留 50 个；create/start/终态落盘，进程死亡后启动时 `_reap_orphans` 补录为 failed（[pipeline_jobs.py:162-197](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py#L162-L197)）。
- **单飞去重**：pending ∨ running 均视为活跃，复用已有任务（[pipeline_jobs.py:200-255](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py#L200-L255)）。
- **卡死判定**：进度停滞阈值（普通 1200s / 长任务 1800s，可配置）+ 总时长硬上限 12h（[pipeline_jobs.py:38-44](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py#L38-L44)）；协作式终止：置 cancel flag → 僵尸线程在下个进度回调抛 `JobCancelledError` 自行退出（[pipeline_jobs.py:367-437](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py#L367-L437)）。
- **重任务互斥执行槽**：带所有权 token，`try_acquire_run_slot/release_run_slot`，防止 reap 后僵尸线程与新任务并发写同一 parquet（[pipeline_jobs.py:500-528](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py#L500-L528)）。

### 3.4 前向扩展历史（`extend_history.py`）

用户从日K卡片手动触发，指定往前补 x 天/月/年。流程：取当前最早日期 → 向前拉日K batch → 向前拉除权因子 → 全量重算 enriched → 刷新视图+缓存（[extend_history.py:102-227](file:///c:/Code/tick-stock-panel/backend/app/services/extend_history.py#L102-L227)）。完全独立于 `daily_pipeline.run_now()`，只复用 kline_sync / indicators.pipeline / pipeline_jobs / KlineRepository 基础设施（[extend_history.py:1-16](file:///c:/Code/tick-stock-panel/backend/app/services/extend_history.py#L1-L16)）。

### 3.5 数据修正/补全（`repair_daily.py`）

`run_repair_daily` 通过 `run_now(override_start_date=start_date)` 把日K/除权/指数拉取起点统一设为用户指定日期，其余流程与盘后管道完全一致（[repair_daily.py:27-57](file:///c:/Code/tick-stock-panel/backend/app/services/repair_daily.py#L27-L57)）。典型场景：停机一天导致的本地缺口。`end_date` 为保留参数未使用。

### 3.6 数据完整性自检与自动修复（`data_integrity.py`）

- **检测判据**（quote_ts 毫秒 Unix 时间戳，仅实时 flush 写真实值）：null→batch 权威历史完整；早于当日 15:00→盘中快照坏；≥15:00→尾盘定版完整；停牌残留零成交行忽略；今天不校验；分区缺失→缺口（[data_integrity.py:7-17](file:///c:/Code/tick-stock-panel/backend/app/services/data_integrity.py#L7-L17)）。成本：每分区只读 parquet 元数据 statistics（~0.5ms/分区）。
- **扫描范围**：最近 7 个自然日内、今天之前的交易日；只报「尾部缺口」（晚于本地最新分区），历史内部空洞走独立 laggards 告警（[data_integrity.py:168-221](file:///c:/Code/tick-stock-panel/backend/app/services/data_integrity.py#L168-L221)）。
- **自动修复窗口**：最早坏日距今 ≤5 自然日才自动修复；`launch_integrity_repair` 复用 repair_daily 管道 + JobStore 体系（run slot + 实时 paused 互斥）（[data_integrity.py:283-373](file:///c:/Code/tick-stock-panel/backend/app/services/data_integrity.py#L283-L373)）。
- **启动自检**：`boot_integrity_check` 在启动 30s 后由后台线程执行（[main.py:202-204](file:///c:/Code/tick-stock-panel/backend/app/main.py#L202-L204)）；自动修复前先 `prune_enriched_partitions` 删除坏分区（股票 enriched 增量重算只算不存在的日期，需先删掉盘中快照分区）（[data_integrity.py:243-269](file:///c:/Code/tick-stock-panel/backend/app/services/data_integrity.py#L243-L269)）。

### 3.7 扩展数据（`ext_data.py` / `ext_presets.py` / `ext_pull.py`）

- **配置模型**：`ExtConfig`（id/label/mode[snapshot|timeseries]/fields/symbol_map/code_map/pull），`PullConfig`（url/method/response_path/field_map/schedule_minutes/时间窗口/date_param/auth）（[ext_data.py:21-212](file:///c:/Code/tick-stock-panel/backend/app/services/ext_data.py#L21-L212)）。配置按 `data/ext_data/{id}/config.json` 独立目录存放，`ExtConfigStore` 带目录签名缓存（[ext_data.py:239-337](file:///c:/Code/tick-stock-panel/backend/app/services/ext_data.py#L239-L337)）。
- **文件解析与存储**：CSV（含 GBK/GB18030 自动转 UTF-8 编码探测）、Excel；snapshot 模式覆盖写 `part.parquet`，timeseries 按日分区（[ext_data.py:540-649](file:///c:/Code/tick-stock-panel/backend/app/services/ext_data.py#L540-L649)）。symbol 标准化优先查 instruments 维表，兜底 6开头→.SH。
- **内置预设**：概念（ext_gn_ths）与行业（ext_hy_ths）两条内置配置，启动时仅创建 config.json、不拉取数据（用户手动获取）（[ext_presets.py:237-258](file:///c:/Code/tick-stock-panel/backend/app/services/ext_presets.py#L237-L258)）；接入点在 lifespan（[main.py:224-225](file:///c:/Code/tick-stock-panel/backend/app/main.py#L224-L225)）。
- **定时拉取**：`PullScheduler` 为每个 enabled 配置维护 asyncio 任务，跨线程增删走 `call_soon_threadsafe`（[ext_pull.py:382-529](file:///c:/Code/tick-stock-panel/backend/app/services/ext_pull.py#L382-L529)）；每轮重读最新配置，改间隔即时生效；支持每日时间窗口、API Key 鉴权注入（bearer/header/query 三型）、日期参数回补。
- **历史回补**：`backfill_history` 按本地交易日逐日回补（幂等，已有分区跳过），单日失败不中断；429 限流退避后重试一次，连续 3 天中止（[ext_pull.py:286-374](file:///c:/Code/tick-stock-panel/backend/app/services/ext_pull.py#L286-L374)）。
- **API Key 安全**：Key 只存 `secrets.json`（`ext_{config_id}_api_key`），环境变量 `EXT_{ID}_API_KEY` 兜底，不落 config.json（[ext_data.py:136-147](file:///c:/Code/tick-stock-panel/backend/app/services/ext_data.py#L136-L147)）。
- **视图刷新**：`_refresh_views` 注册 `ext_{config_id}` DuckDB 视图（[ext_data.py](file:///c:/Code/tick-stock-panel/backend/app/api/ext_data.py) 内，待确认行号）。

## 4. 数据流 / 调用链

### 4.1 盘后管道主链路

```
APScheduler 定时触发 (盘后 15:35)
  → jobs/daily_pipeline.py start_scheduler → run_now()
      ├─ Step 0  sync_instruments → KlineRepository 维表 (instruments.parquet)
      ├─ Step 1  kline_sync.sync_daily_batch / sync_and_persist_daily_batch (SDK klines.batch)
      ├─ Step 1.5  kline_sync.sync_adj_factor (SDK ex_factors, 增量合并, 原子写 all.parquet)
      ├─ Step 2  indicators.pipeline.run_pipeline (全量/增量/除权影响重算 + prune_enriched_partitions)
      ├─ Step 2.3  指数/ETF 同步 (物理分开: kline_index_daily / kline_etf_daily)
      ├─ Step 2.5  kline_sync.sync_minute_batch (分段拉取 + 流式落盘, date= 分区)
      ├─ Step 2.6/2.7  regime/主线增量计算 (默认关闭)
      └─ Step 3  刷新 DuckDB 视图 (kline_daily/enriched/minute/adj_factor/...)
  → 完整性自愈: scan_recent_integrity → 检测到坏分区 → launch_integrity_repair
```

### 4.2 手动任务调用链（前向扩展 / 修正 / 重建 enriched）

```
前端 Data.tsx 点击 → /api/data 或 /api/ext-data 或 /api/pipeline
  → extend_history.run_extend_history   (独立链路, 复用 kline_sync + indicators.run_pipeline)
  → repair_daily.run_repair_daily       (复用 daily_pipeline.run_now, override_start_date)
  → 进度经 on_progress 回调 → job_store.progress() → /api/pipeline/jobs/{id} 轮询
```

### 4.3 扩展数据链路

```
前端上传 CSV/Excel / 录入 JSON / 配置 URL 拉取
  → /api/ext-data CRUD → ExtConfigStore 落 config.json
  → ext_data.parse_upload_file / rows_to_parquet → write_ext_parquet (snapshot: part.parquet / timeseries: date= 分区)
  → PullScheduler 定时 (enabled 配置) → fetch_and_ingest → fetch_rows_for_date → rows_to_parquet
  → _refresh_views 注册 ext_{config_id} 视图 → 分析页/策略可关联 (symbol 标准化经 instruments 维表)
  → 缓存失效: _invalidate_ext_derived → ext_factors.invalidate_ext_caches
```

### 4.4 前端 → API 数据查询

```
useDataStatus / usePipelineJobs / useCapabilities / usePreferences / useQuoteStatus / useExtDataConfigs
  → GET /api/data/status, /api/pipeline/jobs, /api/preferences, ...
  → routeCapUsable / mergedCaps 能力路由门控 (套餐能力 + 路由可用性合并)
  → 11 张画像卡片 (STAGE_CARD 映射管道阶段 → 卡片)
```

## 5. 关键数据结构

### 5.1 任务 Job 记录（JobStore，`data/job_store/{id}.json`）

```json
{
  "id": "uuid-hex10", "status": "pending|running|succeeded|failed",
  "stage": "sync_daily", "progress": 0-100, "stage_pct": 0-100,
  "log": [{"ts": "...", "stage": "...", "msg": "...", "_skip": true}],
  "started_at": "...Z", "last_progress_at": "...Z", "finished_at": "...Z",
  "duration_s": 12.3, "result": {}, "error": "", "timeout_s": 1200
}
```

### 5.2 扩展数据配置（`data/ext_data/{id}/config.json`）

```json
{
  "id": "ext_gn_ths", "label": "扩展概念",
  "mode": "snapshot|timeseries",
  "fields": [{"name": "symbol", "dtype": "string|int|float|bool", "label": "标的代码"}],
  "symbol_map": {"type": "mapped", "col": "股票代码"} | {"type": "computed", "from": "code", "method": "strip_exchange"},
  "code_map": {...},
  "pull": {
    "url": "...", "method": "GET|POST", "headers": {}, "body": "...",
    "response_path": "data.list", "field_map": {"外字段": "内字段"},
    "schedule_minutes": 1440, "enabled": false,
    "time_window_start": "HH:MM", "time_window_end": "HH:MM",
    "date_param": "date", "auth": {"type": "none|bearer|header|query", "header": "...", "param": "..."},
    "last_run": "...", "last_status": "success|error|skipped", "last_message": "...", "last_rows": 123, "next_run": "..."
  }
}
```

### 5.3 数据画像缓存（`data.py` 内存缓存）

- `_table_cache: dict[str, tuple[float, Any]]` — 表统计，TTL 30s（小表）/120s（大表）
- `_storage_cache` — 磁盘占用，TTL 60s
- `invalidate_data_cache(table)` — 精确失效；`POST /clear` 清全部 + repo.clear_cache()

### 5.4 完整性判定（`IntegrityIssue`）

```python
@dataclass(frozen=True)
class IntegrityIssue:
    day: date          # 坏分区日期
    table: str         # kline_daily / kline_etf_daily / kline_index_daily
    kind: str          # "snapshot"=盘中快照 | "missing"=分区缺失
```

## 6. 扩展与修改指南

### 6.1 新增数据画像卡片

1. 后端在 `GET /api/data/status` 返回新表统计（沿用 `_table_cache` 缓存模式与分区目录计数优化）。
2. 前端在 [Data.tsx](file:///c:/Code/tick-stock-panel/frontend/src/pages/Data.tsx) 的画像卡片区新增卡片组件，复用 StatCard/StatGrid 模式。
3. 若新表参与实时 flush，需在 [data_integrity.py](file:///c:/Code/tick-stock-panel/backend/app/services/data_integrity.py) `_DAILY_TABLES`/`TABLE_FAMILY` 登记（否则完整性自检不覆盖）。

### 6.2 新增盘后管道阶段

在 [daily_pipeline.py](file:///c:/Code/tick-stock-panel/backend/app/jobs/daily_pipeline.py) `run_now()` 的步骤序列中插入新阶段，并同步更新前端 `STAGE_CARD` 阶段→卡片映射与文案；新阶段进度通过 `on_progress(stage, pct, msg)` 上报。注意 `PipelineStageError` 软失败累积语义——阶段失败不中断但最终使任务标记 failed。

### 6.3 新增扩展数据预设

参考 [ext_presets.py](file:///c:/Code/tick-stock-panel/backend/app/services/ext_presets.py) 的 `_concept_preset()`/`_industry_preset()`：定义 `ExtConfig`（含 PullConfig）+ 结构转换函数（`_flatten_*`），并在 `_presets()` 注册；如需定时拉取路径也走转换，需在 [ext_pull.py](file:///c:/Code/tick-stock-panel/backend/app/services/ext_pull.py) `_apply_preset_flatten` 登记。预设必须遵守「启动只建配置不拉数据」「已存在则跳过」约定。

### 6.4 修改同步/计算口径

所有同步收敛于 [kline_sync.py](file:///c:/Code/tick-stock-panel/backend/app/services/kline_sync.py)（`_normalize_daily/_normalize_minute/_normalize_adj_factor`）与 indicators pipeline。改动同步/计算必须：
- 保持北京墙钟 naive datetime（分钟K `_enforce_minute_beijing_wallclock`）、复权/原始价口径、股票/ETF/指数分开存储；
- 若改 Parquet schema 或列，更新 `/api/data/schema/{table}` 的静态定义与前端 Schema 弹窗；
- 改缓存读写时列出受影响缓存层（文件 → 内存 → generation → SSE → 前端）。

### 6.5 修改任务超时/并发策略

阈值集中在 [pipeline_jobs.py:38-44](file:///c:/Code/tick-stock-panel/backend/app/services/pipeline_jobs.py#L38-L44)（常量 + 可配置项）；重任务互斥槽（`try_acquire_run_slot/release_run_slot`）与 JobStore 生命周期强耦合，修改并发策略必须保持所有权 token 语义。

## 7. 依赖关系

| 依赖 | 用途 | 说明 |
| --- | --- | --- |
| `app.tickflow.repository.KlineRepository` | Parquet 读写/视图 | 所有数据落盘与 DuckDB 视图的唯一入口 |
| `app.tickflow.capabilities.CapabilitySet` | 能力路由门控 | `Cap.KLINE_DAILY_BATCH` 等控制分支（extend_history 里用于标的池解析与除权因子分支） |
| `app.indicators.pipeline.run_pipeline` | enriched 计算 | 全量/增量重算；extend_history 与盘后管道共用 |
| `app.services.pipeline_jobs.job_store` | 任务注册表 | 进度上报/单飞/卡死检测/互斥槽 |
| `app.tickflow.pools.get_pool` | 标的池解析 | `CN_Equity_A` / watchlist / DEMO_SYMBOLS |
| `app.services.preferences` | 偏好配置 | 数据源超时、除权因子 provider、调度时间 |
| `app.services.dragon_tiger._local_trading_days` | 交易日历 | ext_pull 回补按本地交易日（需先同步日K） |
| `app.secrets_store` | API Key 安全存储 | ext 拉取鉴权 Key，不落 config.json |
| `app.factors.ext_factors.invalidate_ext_caches` | 扩展帧缓存失效 | 扩展数据变更后必须失效派生缓存 |
| `app.market_time.CN_TZ` | 北京时间 | 完整性判定/时区转换 |

### 生命周期装配（main.py lifespan）

- 启动 30s 后台线程执行 `boot_integrity_check`（[main.py:202-204](file:///c:/Code/tick-stock-panel/backend/app/main.py#L202-L204)）
- `ensure_builtin_presets` 先于 `pull_scheduler.refresh`（全新部署时 scheduler 才能读到预设配置）（[main.py:221-233](file:///c:/Code/tick-stock-panel/backend/app/main.py#L221-L233)）
- `start_scheduler` 注册全部定时任务（[main.py:171-174](file:///c:/Code/tick-stock-panel/backend/app/main.py#L171-L174)）
- 路由注册：`pipeline.router` / `data.router` / `ext_data.router`（[main.py:483-485](file:///c:/Code/tick-stock-panel/backend/app/main.py#L483-L485)）

## 8. 常见问题（FAQ）

**Q1：任务卡住/进度不动了怎么办？**
reap_stale 在 `/run` 与 `/jobs/{id}` 轮询端点都会检查：进度停滞超过阈值（普通 1200s / 长任务 1800s，可在数据源设置调整）或总时长超 12h 会被协作式取消；可手动 `POST /api/pipeline/jobs/{id}/cancel`。卡死在单个无限阻塞网络读（协作式失效）时需重启进程。

**Q2：为什么「今天」数据被判定为盘中快照？**
quote_ts < 当日 15:00 且非 batch 权威行 → 停机前实时 flush 残留，技术指标会错。盘后管道/自动修复会删坏分区重算；超过 5 天窗口需在数据页手动执行数据修正。

**Q3：扩展数据定时拉取不执行？**
检查：PullConfig `enabled` 是否为 true（预设出厂为 false）；是否在 `time_window_start/end` 时间窗口内；是否配置了 auth 但未填 API Key（fail-closed 报错）；`date_param` 缺失时接口无法回补。

**Q4：概念/行业扩展表为什么启动时不自动拉数据？**
设计约定（#199）：内置预设仅创建 config.json，用户在概念/行业页手动「获取数据」触发，避免启动网络请求阻塞（[ext_presets.py:1-15](file:///c:/Code/tick-stock-panel/backend/app/services/ext_presets.py#L1-L15)）。

**Q5：为什么清除数据后立即同步仍报「已有数据」？**
`POST /clear` 会清 Parquet + 同步历史 + Polars 缓存 + DuckDB 视图 + alerts；若仍异常，检查是否被 EnrichedPublication 保护拦截（有公开记录时拒绝清空），或前端 React Query 缓存未失效（需确认失效前缀覆盖）。

**Q6：CSV 中文乱码？**
上传解析前自动做编码探测：UTF-8 → GB18030 → GBK → GB2312 → BIG5，转成 UTF-8 再交给 Polars（[ext_data.py:516-537](file:///c:/Code/tick-stock-panel/backend/app/services/ext_data.py#L516-L537)）。若全部失败会返回原始错误而非静默。

## 9. 待确认项

- [data.py](file:///c:/Code/tick-stock-panel/backend/app/api/data.py) `GET /status` 返回字段的精确行号与 indicator_ready 语义（文档引用为 46-69 待核）。
- `ext_data.py`（API 层）`_refresh_views` 精确行号。
- `daily_pipeline.py` 定时复盘（`_run_scheduled_review`）精确行号。
- 前端 `useDataStatus` 等 hook 的失效前缀与 `queryKeys.ts` 的对应关系（涉及 Q5 缓存链路）。
