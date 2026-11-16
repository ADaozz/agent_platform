<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import PageHeader from '@/components/PageHeader.vue'
import KpiCard from '@/components/KpiCard.vue'
import EChart from '@/components/EChart.vue'
import AppIcon from '@/components/AppIcon.vue'
import { tr } from '@/composables/preferences'
import { getUsageOverview, type UsageOverview } from '@/api/agentRuntime'
import { dailyUsageOption } from '@/utils/telemetryChart'

const loading = ref(false)
const error = ref('')
const overview = ref<UsageOverview | null>(null)
const days = ref(30)
const chartHost = ref<HTMLElement | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    overview.value = await getUsageOverview(days.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    overview.value = null
  } finally {
    loading.value = false
  }
}

function switchDays(next: number) {
  if (days.value === next) return
  days.value = next
  load()
}

onMounted(load)

const totals = computed(() => overview.value?.totals)
const flashRates = computed(() => overview.value?.rates_cny_per_m?.['deepseek-flash'] ?? null)

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
    <PageHeader
      :title="tr('用量仪表盘')"
      :desc="tr('按天统计模型 Tokens 与估算费用，数据来自会话生成指标。')"
    >
      <div class="flex flex-wrap items-center gap-2">
        <div class="segmented" role="tablist" aria-label="window">
          <button
            v-for="n in [7, 30, 90]"
            :key="n"
            type="button"
            role="tab"
            :aria-selected="days === n"
            @click="switchDays(n)"
          >
            {{ n }}D
          </button>
        </div>
        <button class="btn-ghost !h-8" :disabled="loading" @click="load">
          <AppIcon name="refresh" class="!text-[18px]" :class="{ 'animate-spin': loading }" />
          {{ tr('刷新') }}
        </button>
      </div>
    </PageHeader>

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
            <span class="meta-id">CHART-01</span>
            <h2 class="panel-title">{{ tr('日用量轨迹') }}</h2>
            <p class="panel-note">{{ tr('薄荷绿 = Tokens · 航天橙 = 估算费用') }}</p>
          </div>
          <span class="meta-guide">{{ tr(overview.cost_note) }}</span>
        </header>
        <div class="chart-frame">
          <EChart v-if="chartOption" :option="chartOption" height="320px" />
          <p v-else class="py-20 text-center font-mono text-xs tracking-wider text-ink-faint">NO SERIES</p>
        </div>
      </section>

      <div v-if="flashRates" class="rate-card">
        <div class="rate-head">
          <span class="meta-id">NOTE-RATE</span>
          <strong>{{ tr('DeepSeek Flash 刊例（元/百万 tok）') }}</strong>
        </div>
        <div class="rate-grid">
          <div class="rate-col">
            <span class="rate-band">{{ tr('空闲') }}</span>
            <span>{{ tr('缓存命中') }} {{ flashRates.off_peak.cache_hit }}</span>
            <span>{{ tr('缓存未命中') }} {{ flashRates.off_peak.cache_miss }}</span>
            <span>{{ tr('输出') }} {{ flashRates.off_peak.output }}</span>
          </div>
          <div class="rate-col">
            <span class="rate-band">{{ tr('高峰') }}</span>
            <span>{{ tr('缓存命中') }} {{ flashRates.peak.cache_hit }}</span>
            <span>{{ tr('缓存未命中') }} {{ flashRates.peak.cache_miss }}</span>
            <span>{{ tr('输出') }} {{ flashRates.peak.output }}</span>
          </div>
        </div>
        <p class="rate-note">
          {{ tr('峰时段：北京时间工作日 09:00–12:00、14:00–18:00；周末与法定节假日全天空闲') }}
        </p>
      </div>
    </template>
  </div>
</template>

<style scoped>
.panel-quiet {
  position: relative;
  border: 1px solid color-mix(in srgb, var(--color-line) 55%, transparent);
  border-radius: 14px;
  background:
    linear-gradient(var(--glass), var(--glass)),
    var(--color-card);
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
.meta-id {
  display: block;
  margin-bottom: 0.2rem;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.16em;
  color: var(--color-ink-faint);
}
.panel-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 650;
  letter-spacing: 0.02em;
  color: var(--color-ink);
}
.panel-note {
  margin-top: 0.2rem;
  font-size: 12px;
  color: var(--color-ink-muted);
}
.meta-guide {
  max-width: 36ch;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.5;
  letter-spacing: 0.04em;
  color: var(--color-ink-faint);
  text-align: right;
}
.chart-frame {
  padding: 0.5rem 0.75rem 0.75rem;
}
.rate-card {
  border: 1px solid color-mix(in srgb, var(--color-line) 55%, transparent);
  border-radius: 14px;
  padding: 1rem 1.25rem 1.1rem;
  background: color-mix(in srgb, var(--color-card) 92%, transparent);
}
.rate-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.5rem 0.85rem;
  margin-bottom: 0.75rem;
}
.rate-head strong {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-ink);
}
.rate-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem 1.5rem;
}
.rate-col {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-ink-muted);
}
.rate-band {
  color: var(--color-ink);
  font-weight: 600;
  letter-spacing: 0.06em;
}
.rate-note {
  margin-top: 0.85rem;
  font-size: 11px;
  line-height: 1.55;
  color: var(--color-ink-faint);
}
@media (max-width: 767px) {
  .rate-grid {
    grid-template-columns: 1fr;
  }
}
</style>
