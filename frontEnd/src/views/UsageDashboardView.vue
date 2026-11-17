<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import PageHeader from '@/components/PageHeader.vue'
import UsageModelFilter from '@/components/UsageModelFilter.vue'
import KpiCard from '@/components/KpiCard.vue'
import EChart from '@/components/EChart.vue'
import AppIcon from '@/components/AppIcon.vue'
import { tr } from '@/composables/preferences'
import { getUsageOverview, type UsageOverview } from '@/api/agentRuntime'
import { MODEL_PRESETS } from '@/utils/modelPresets'
import { dailyUsageOption } from '@/utils/telemetryChart'

const loading = ref(false)
const error = ref('')
const overview = ref<UsageOverview | null>(null)
const days = ref(30)
const provider = ref('')
const model = ref('')
let loadRevision = 0
const providerLabel = (id: string) => tr(MODEL_PRESETS.find(p => p.id === id)?.label ?? (id === 'other' ? '其他服务商' : id))
const providerOptions = computed(() => overview.value?.filters?.providers ?? MODEL_PRESETS.map(p => p.id))
const modelChoices = computed(() => overview.value?.filters?.models ?? MODEL_PRESETS.flatMap(p => p.models.map(m => ({ provider: p.id, id: m.key }))))
const providerChoices = computed(() => providerOptions.value.map(id => ({ id, label: providerLabel(id) })))
const chartHost = ref<HTMLElement | null>(null)

async function load() {
  const revision = ++loadRevision
  loading.value = true
  error.value = ''
  try {
    const result = await getUsageOverview(days.value, { provider: provider.value, model: model.value })
    if (revision === loadRevision) overview.value = result
  } catch (e) {
    if (revision !== loadRevision) return
    error.value = e instanceof Error ? e.message : String(e)
    overview.value = null
  } finally {
    if (revision === loadRevision) loading.value = false
  }
}

function selectModel(nextProvider: string, nextModel: string) { provider.value = nextProvider; model.value = nextModel; void load() }

function switchDays(next: number) {
  if (days.value === next) return
  days.value = next
  load()
}

onMounted(load)

const totals = computed(() => overview.value?.totals)
const rateCards = computed(() => {
  const rates = overview.value?.rates_cny_per_m
  if (!rates) return []
  return Object.entries(rates).map(([model, bands]) => {
    const peaked = bands.off_peak.cache_hit !== bands.peak.cache_hit
      || bands.off_peak.cache_miss !== bands.peak.cache_miss
      || bands.off_peak.output !== bands.peak.output
    return {
      model,
      cacheHit: peaked ? `${bands.off_peak.cache_hit} / ${bands.peak.cache_hit}` : String(bands.off_peak.cache_hit),
      cacheMiss: peaked ? `${bands.off_peak.cache_miss} / ${bands.peak.cache_miss}` : String(bands.off_peak.cache_miss),
      output: peaked ? `${bands.off_peak.output} / ${bands.peak.output}` : String(bands.off_peak.output),
    }
  })
})

function formatTok(n: number | undefined) {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return n.toLocaleString()
}

function formatCost(n: number | undefined) {
  if (n == null) return '—'
  return n < 0.01 ? n.toFixed(4) : n.toFixed(2)
}

const chartOption = computed<EChartsOption | null>(() => {
  const data = overview.value
  if (!data) return null
  const host = chartHost.value ?? document
  return dailyUsageOption(data.daily, host)
})
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-4">
    <PageHeader :title="tr('用量仪表盘')">
      <button class="btn-ghost refresh-usage" :disabled="loading" @click="load"><AppIcon name="refresh" :class="{ 'animate-spin': loading }" />{{ tr('刷新') }}</button>
    </PageHeader>

    <div class="filter-toolbar usage-filters">
      <div class="segmented" role="tablist" :aria-label="tr('统计时间范围')">
        <button v-for="n in [7, 30, 90]" :key="n" type="button" role="tab" :aria-selected="days === n" @click="switchDays(n)">{{ n }}D</button>
      </div>
      <UsageModelFilter :providers="providerChoices" :models="modelChoices" :provider="provider" :model="model" @select="selectModel" />
    </div>

    <p v-if="error" class="text-sm text-danger">{{ error }}</p>

    <div v-if="loading && !overview" class="panel-quiet px-4 py-16 text-center text-sm text-ink-muted">
      {{ tr('加载遥测数据…') }}
    </div>

    <template v-else-if="overview && totals">
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard :title="tr('总 Tokens')" :value="formatTok(totals.total_tokens)" icon="telemetry" suffix="tok" />
        <KpiCard
          :title="tr('输入 / 输出')"
          :value="formatTok(totals.input_tokens)"
          icon="route"
          :suffix="`/ ${formatTok(totals.output_tokens)}`"
        />
        <KpiCard :title="tr('估算费用')" :value="formatCost(totals.cost_cny)" icon="tag" suffix="CNY" />
        <KpiCard :title="tr('调用 / 会话')" :value="totals.calls" icon="console" :suffix="`/ ${totals.sessions}`" />
      </div>

      <section ref="chartHost" class="panel-quiet">
        <header class="panel-meta">
          <div>
            <h2 class="panel-title">{{ tr('日用量轨迹') }}</h2>
          </div>
        </header>
        <div class="chart-frame">
          <EChart v-if="chartOption" :option="chartOption" height="320px" />
          <p v-else class="py-20 text-center font-mono text-xs tracking-wider text-ink-faint">NO SERIES</p>
        </div>
      </section>

      <details v-if="rateCards.length" class="rate-card">
        <summary class="rate-title">{{ tr('模型价格参考') }}<AppIcon name="expand_more" /></summary>
        <div class="rate-table-wrap">
          <table class="rate-table" :aria-label="tr('预设模型刊例（元/百万 tok）')">
            <thead><tr><th scope="col">{{ tr('模型') }}</th><th scope="col">{{ tr('缓存命中') }}</th><th scope="col">{{ tr('缓存未命中') }}</th><th scope="col">{{ tr('输出') }}</th></tr></thead>
            <tbody>
              <tr v-for="card in rateCards" :key="card.model">
                <th scope="row" class="rate-model-name">{{ card.model }}</th>
                <td>{{ card.cacheHit }}</td><td>{{ card.cacheMiss }}</td><td>{{ card.output }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </template>
  </div>
</template>

<style scoped>
.usage-filters { border-bottom: 0; padding: 0; }
.usage-filters .segmented { flex: 0 0 auto; }
.usage-filters :deep(.usage-model-filter) { flex: 1 1 auto; width: auto; max-width: none; min-width: 0; }
.panel-quiet {
  position: relative;
  border: 1px solid color-mix(in srgb, var(--color-line) 55%, transparent);
  border-radius: 14px;
  background: var(--color-card);
}
.panel-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.75rem 1.25rem;
  padding: 1rem 1.25rem 0.75rem;
  border-bottom: 1px solid color-mix(in srgb, var(--color-line) 45%, transparent);
}
.panel-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 650;
  letter-spacing: 0.02em;
  color: var(--color-ink);
}
.chart-frame {
  padding: 0.5rem 0.75rem 0.75rem;
}
.rate-card {
  overflow: hidden;
  min-width: 0;
  border: 1px solid var(--color-line);
  border-radius: 10px;
  background: var(--color-card);
}
.rate-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 16px; font-size: 13px; font-weight: 600; color: var(--color-ink); list-style: none; cursor: pointer; }
.rate-title::-webkit-details-marker { display: none; }
.rate-title::marker { content: ''; }
.rate-title:focus-visible { outline: 2px solid var(--color-primary); outline-offset: -2px; }
.rate-title .app-icon { color: var(--color-ink-muted); }
.rate-card[open] .rate-title { border-bottom: 1px solid var(--color-line); }
.rate-card[open] .rate-title .app-icon { transform: rotate(180deg); }
.rate-table-wrap { overflow-x: auto; }
.rate-table { width: 100%; min-width: 500px; border-collapse: collapse; font-size: 12px; font-variant-numeric: tabular-nums; }
.rate-table thead th { padding: 10px 16px; background: var(--color-card); color: var(--color-ink-muted); font-weight: 500; text-align: right; white-space: nowrap; }
.rate-table thead th:first-child { text-align: left; }
.rate-table tbody tr + tr { border-top: 1px solid var(--color-line); }
.rate-table td { padding: 8px 16px; text-align: right; color: var(--color-ink-secondary); white-space: nowrap; }
.rate-table .rate-model-name { padding: 8px 16px; text-align: left; font-family: var(--font-mono); font-weight: 500; color: var(--color-ink); white-space: nowrap; }
@media (max-width: 767px) {
  .chart-frame { padding: 4px 6px 8px; }
  .rate-table :is(th, td) { padding-inline: 12px; }
}
</style>
