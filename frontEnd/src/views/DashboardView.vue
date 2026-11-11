<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { EChartsOption } from 'echarts'
import { getDashboardOverview, type DashboardScope } from '@/api/dashboard'
import { useAuthStore } from '@/stores/auth'
import { LIFECYCLE_ORDER, LIFECYCLE_TAGS, ENV_TAGS, ZONE_LABELS } from '@/constants'
import type { CategoryChartVO, DashboardOverviewVO, LifecycleStatus, PieChartVO } from '@/types'
import KpiCard from '@/components/KpiCard.vue'
import EChart from '@/components/EChart.vue'
import AppIcon from '@/components/AppIcon.vue'
import type { IconName } from '@/icons'

const auth = useAuthStore()
const canViewAll = computed(() => auth.hasPerm('dashboard:view:all'))

const scope = ref<DashboardScope>('mine')
const loading = ref(false)
const overview = ref<DashboardOverviewVO | null>(null)

async function load() {
  loading.value = true
  try {
    overview.value = await getDashboardOverview(scope.value)
  } finally {
    loading.value = false
  }
}

function switchScope(s: DashboardScope) {
  if (scope.value === s) return
  scope.value = s
  load()
}

onMounted(load)

const lifecycleCounts = computed<Record<string, number>>(() => {
  const map: Record<string, number> = {}
  for (const item of overview.value?.vmByLifecycle.data ?? []) {
    map[item.name] = item.value
  }
  return map
})

const lifecycleIcons: Record<LifecycleStatus, IconName> = {
  creating: 'add_circle',
  running: 'play_circle',
  stopped: 'stop_circle',
  pending_delete: 'hourglass_top',
  destroyed: 'delete',
}

function pieOption(pie: PieChartVO | undefined, nameMap?: Record<string, string>): EChartsOption | null {
  if (!pie) return null
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 12 } },
    series: [
      {
        type: 'pie',
        radius: ['45%', '68%'],
        center: ['50%', '44%'],
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { show: false },
        data: pie.data.map((d) => ({ ...d, name: nameMap?.[d.name] ?? d.name })),
      },
    ],
  }
}

const appStatusOption = computed(() =>
  pieOption(overview.value?.appByStatus, { running: '运行中', stopped: '已停止' }),
)
const envOption = computed(() =>
  pieOption(overview.value?.vmByEnv, Object.fromEntries(Object.entries(ENV_TAGS).map(([k, v]) => [k, v.label]))),
)
const zoneOption = computed(() => pieOption(overview.value?.vmByNetworkZone, ZONE_LABELS))

const trendOption = computed<EChartsOption | null>(() => {
  const trend = overview.value?.vmCreateTrend
  if (!trend) return null
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: trend.categories, axisLine: { lineStyle: { color: '#e5e7eb' } } },
    yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#f3f4f6' } } },
    series: trend.series.map((s) => ({
      ...s,
      type: 'line' as const,
      smooth: true,
      symbolSize: 6,
      lineStyle: { width: 2.5, color: '#2563eb' },
      itemStyle: { color: '#2563eb' },
      areaStyle: { color: 'rgba(37, 99, 235, 0.08)' },
    })),
  }
})

function barOption(chart: CategoryChartVO | null | undefined): EChartsOption | null {
  if (!chart || chart.categories.length === 0) return null
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 10, right: 30, top: 10, bottom: 10, containLabel: true },
    xAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#f3f4f6' } } },
    yAxis: {
      type: 'category',
      data: [...chart.categories].reverse(),
      axisLine: { show: false },
      axisTick: { show: false },
    },
    series: chart.series.map((s) => ({
      name: s.name,
      type: 'bar' as const,
      barWidth: 14,
      itemStyle: { color: '#2563eb', borderRadius: [0, 4, 4, 0] },
      data: [...s.data].reverse(),
    })),
  }
}

const ownerRankOption = computed(() => barOption(overview.value?.ownerRank))
const physicalHostOption = computed(() => barOption(overview.value?.physicalHostDistribution))
</script>

<template>
  <div class="space-y-4">
    <!-- 页头 -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-ink">
          {{ scope === 'all' ? '全局概览' : '我的资源概览' }}
        </h1>
        <p class="mt-0.5 text-sm text-ink-muted">系统资源及运行状态汇总</p>
      </div>
      <div class="flex items-center gap-2">
        <div v-if="canViewAll" class="flex rounded-md border border-line bg-white p-0.5">
          <button
            class="rounded px-3 py-1 text-sm transition-colors"
            :class="scope === 'mine' ? 'bg-primary font-medium text-white' : 'text-ink-secondary hover:bg-gray-50'"
            @click="switchScope('mine')"
          >
            我的
          </button>
          <button
            class="rounded px-3 py-1 text-sm transition-colors"
            :class="scope === 'all' ? 'bg-primary font-medium text-white' : 'text-ink-secondary hover:bg-gray-50'"
            @click="switchScope('all')"
          >
            全局
          </button>
        </div>
        <button class="btn-ghost !h-8" :disabled="loading" @click="load">
          <AppIcon name="refresh" class="!text-[18px]" :class="{ 'animate-spin': loading }" />
          刷新
        </button>
      </div>
    </div>

    <template v-if="overview">
      <!-- KPI 卡片 -->
      <div class="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-5" :class="{ 'xl:!grid-cols-6': scope === 'all' }">
        <KpiCard title="虚机总量" :value="overview.kpi.vmHostCount" icon="dns" suffix="实例" />
        <KpiCard title="运行中虚机" :value="overview.kpi.vmHostRunningCount" icon="play_circle" suffix="实例" />
        <KpiCard title="应用服务" :value="overview.kpi.vmAppCount" icon="apps" suffix="个" />
        <KpiCard title="CPU 核数" :value="overview.kpi.cpuCoresTotal" icon="memory" suffix="核" />
        <KpiCard title="内存容量" :value="overview.kpi.memoryGbTotal" icon="sd_card" suffix="GB" />
        <KpiCard v-if="scope === 'all' && overview.kpi.userCount != null" title="系统用户" :value="overview.kpi.userCount" icon="group" suffix="人" />
      </div>

      <!-- 生命周期 + 应用状态 -->
      <div class="grid gap-4 xl:grid-cols-3">
        <div class="card p-5 xl:col-span-2">
          <h2 class="text-base font-semibold text-ink">虚拟机生命周期状态</h2>
          <div class="mt-6 flex items-center justify-between px-2">
            <template v-for="(status, i) in LIFECYCLE_ORDER" :key="status">
              <div class="flex flex-col items-center gap-2">
                <div
                  class="flex h-11 w-11 items-center justify-center rounded-full border"
                  :class="(lifecycleCounts[status] ?? 0) > 0 ? 'border-primary/30 bg-primary-light text-primary' : 'border-line bg-gray-50 text-ink-faint'"
                >
                  <AppIcon :name="lifecycleIcons[status]" />
                </div>
                <span class="text-xs text-ink-muted">{{ LIFECYCLE_TAGS[status]?.label }}</span>
                <span class="text-xl font-semibold" :class="(lifecycleCounts[status] ?? 0) > 0 ? 'text-ink' : 'text-ink-faint'">
                  {{ lifecycleCounts[status] ?? 0 }}
                </span>
              </div>
              <div v-if="i < LIFECYCLE_ORDER.length - 1" class="mx-1 mb-10 h-px flex-1 bg-line"></div>
            </template>
          </div>
        </div>
        <div class="card p-5">
          <h2 class="text-base font-semibold text-ink">应用服务状态</h2>
          <EChart :option="appStatusOption" height="240px" />
        </div>
      </div>

      <!-- 环境 / 网段 / 趋势 -->
      <div class="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <div class="card p-5">
          <h2 class="text-base font-semibold text-ink">虚机环境分布</h2>
          <EChart :option="envOption" height="240px" />
        </div>
        <div class="card p-5">
          <h2 class="text-base font-semibold text-ink">虚机网段分布</h2>
          <EChart :option="zoneOption" height="240px" />
        </div>
        <div class="card p-5 lg:col-span-2">
          <h2 class="text-base font-semibold text-ink">虚机新增趋势（按月）</h2>
          <EChart :option="trendOption" height="240px" />
        </div>
      </div>

      <!-- 全局视图专属 -->
      <div v-if="scope === 'all'" class="grid gap-4 lg:grid-cols-2">
        <div class="card p-5">
          <h2 class="text-base font-semibold text-ink">Owner 虚机数排行 Top10</h2>
          <EChart v-if="ownerRankOption" :option="ownerRankOption" height="280px" />
          <p v-else class="py-16 text-center text-sm text-ink-faint">暂无数据</p>
        </div>
        <div class="card p-5">
          <h2 class="text-base font-semibold text-ink">宿主机分布 Top10</h2>
          <EChart v-if="physicalHostOption" :option="physicalHostOption" height="280px" />
          <p v-else class="py-16 text-center text-sm text-ink-faint">暂无数据</p>
        </div>
      </div>
    </template>

    <div v-else-if="loading" class="card flex items-center justify-center py-24 text-sm text-ink-muted">
      加载中…
    </div>
  </div>
</template>
