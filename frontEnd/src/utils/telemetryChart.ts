import type { EChartsOption } from 'echarts'

/** 从设计 token 读取遥测图配色，跟随 dark/light */
export function telemetryPalette(el: HTMLElement | Document = document) {
  const css = getComputedStyle(el instanceof Document ? el.documentElement : el)
  const read = (name: string, fallback: string) => (css.getPropertyValue(name).trim() || fallback)
  return {
    ink: read('--color-ink', '#181818'),
    muted: read('--color-ink-muted', '#706553'),
    faint: read('--color-ink-faint', '#746a58'),
    line: read('--color-line', '#d1c5ae'),
    card: read('--color-card', '#fbf7ee'),
    page: read('--color-page', '#f5eddc'),
    mint: read('--color-mint', '#83a695'),
    signal: read('--color-signal', '#f36b18'),
    carbon: read('--color-carbon', '#181818'),
    ivory: read('--color-ivory', '#f5eddc'),
    glass: read('--chrome-glass', 'rgba(24,24,24,0.07)'),
    glassEdge: read('--chrome-glass-edge', 'rgba(24,24,24,0.12)'),
    mono: read('--font-mono', 'IBM Plex Mono, monospace'),
  }
}

function glassTooltip(p: ReturnType<typeof telemetryPalette>) {
  // ECharts 浮层不吃极低透明度 glass；黑夜用近实色 panel，保证文字对比度
  const dark = document.documentElement.dataset.theme === 'dark'
  return {
    backgroundColor: dark ? 'rgba(36, 35, 32, 0.94)' : 'rgba(251, 247, 238, 0.94)',
    borderColor: dark ? 'rgba(245, 237, 220, 0.18)' : 'rgba(24, 24, 24, 0.12)',
    borderWidth: 1,
    padding: [10, 12] as [number, number],
    textStyle: {
      color: p.ink,
      fontFamily: p.mono,
      fontSize: 11,
      lineHeight: 18,
    },
    extraCssText: [
      'backdrop-filter: blur(12px)',
      '-webkit-backdrop-filter: blur(12px)',
      'border-radius: 8px',
      dark
        ? 'box-shadow: 0 12px 28px -12px rgba(0,0,0,0.65)'
        : 'box-shadow: 0 10px 24px -14px rgba(40,30,10,0.35)',
    ].join('; '),
  }
}

function axisCommon(p: ReturnType<typeof telemetryPalette>) {
  return {
    axisLine: { lineStyle: { color: p.line, width: 1 } },
    axisTick: { length: 4, lineStyle: { color: p.line, width: 1 } },
    axisLabel: {
      color: p.faint,
      fontFamily: p.mono,
      fontSize: 10,
      margin: 10,
    },
    splitLine: {
      show: true,
      lineStyle: { color: p.line, width: 1, opacity: 0.35, type: 'solid' as const },
    },
  }
}

/** 按天：薄荷绿 tokens + 航天橙 cost，渐进绘制 */
export function dailyUsageOption(
  daily: Array<{
    date: string
    input_tokens: number
    output_tokens: number
    total_tokens: number
    cost_cny: number
  }>,
  el?: HTMLElement | Document,
): EChartsOption {
  const p = telemetryPalette(el)
  const cats = daily.map((d) => d.date.slice(5))
  const tokens = daily.map((d) => d.total_tokens)
  const costs = daily.map((d) => d.cost_cny)
  const tip = glassTooltip(p)
  const axis = axisCommon(p)

  return {
    animationDuration: 900,
    animationEasing: 'cubicOut',
    color: [p.mint, p.signal],
    legend: {
      bottom: 0,
      left: 'center',
      itemWidth: 10,
      itemHeight: 6,
      itemGap: 18,
      icon: 'rect',
      textStyle: { color: p.muted, fontFamily: p.mono, fontSize: 10 },
      data: ['TOKENS', 'COST ¥'],
    },
    tooltip: {
      ...tip,
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: { color: p.faint, width: 1, opacity: 0.55 },
        lineStyle: { color: p.faint, width: 1, type: 'dashed', opacity: 0.5 },
      },
      formatter(params: unknown) {
        const items = Array.isArray(params) ? params : [params]
        const first = items[0] as { axisValue?: string; dataIndex?: number }
        const idx = first.dataIndex ?? 0
        const row = daily[idx]
        if (!row) return ''
        return [
          `<div style="opacity:.7;letter-spacing:.12em;margin-bottom:6px">DAY-${row.date}</div>`,
          `IN  ${row.input_tokens.toLocaleString()} tok`,
          `OUT ${row.output_tokens.toLocaleString()} tok`,
          `Σ   ${row.total_tokens.toLocaleString()} tok`,
          `¥   ${row.cost_cny.toFixed(4)}`,
        ].join('<br/>')
      },
    },
    grid: { left: 52, right: 52, top: 28, bottom: 48 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: cats,
      ...axis,
      splitLine: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        name: 'tok',
        nameTextStyle: { color: p.faint, fontFamily: p.mono, fontSize: 10, align: 'right', padding: [0, 6, 0, 0] },
        ...axis,
        splitNumber: 4,
        axisLabel: {
          ...axis.axisLabel,
          formatter: (v: number) => (v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)),
        },
      },
      {
        type: 'value',
        name: '¥',
        nameTextStyle: { color: p.faint, fontFamily: p.mono, fontSize: 10, align: 'left', padding: [0, 0, 0, 6] },
        ...axis,
        splitLine: { show: false },
        splitNumber: 4,
        axisLabel: {
          ...axis.axisLabel,
          formatter: (v: number) => (v >= 1 ? v.toFixed(1) : v.toFixed(3)),
        },
      },
    ],
    series: [
      {
        name: 'TOKENS',
        type: 'line',
        yAxisIndex: 0,
        data: tokens,
        showSymbol: true,
        symbol: 'circle',
        symbolSize: 5,
        itemStyle: { color: p.mint, borderColor: p.mint, borderWidth: 1 },
        lineStyle: { width: 1.75, color: p.mint, shadowBlur: 0 },
        areaStyle: { color: 'transparent' },
        emphasis: { scale: false, itemStyle: { color: p.page, borderColor: p.mint, borderWidth: 1.5 } },
        animationDuration: 1100,
      },
      {
        name: 'COST ¥',
        type: 'line',
        yAxisIndex: 1,
        data: costs,
        showSymbol: true,
        symbol: 'emptyCircle',
        symbolSize: 6,
        itemStyle: { color: p.signal, borderColor: p.signal, borderWidth: 1.25 },
        lineStyle: { width: 1.75, color: p.signal, type: 'solid', shadowBlur: 0 },
        emphasis: { scale: false, itemStyle: { color: p.page, borderColor: p.signal, borderWidth: 1.5 } },
        animationDuration: 1300,
      },
    ],
  }
}

/** 按会话：水平条 — mint tokens，标注 cost */
export function sessionUsageOption(
  sessions: Array<{
    session_id: string
    title: string
    total_tokens: number
    cost_cny: number
  }>,
  el?: HTMLElement | Document,
  limit = 12,
): EChartsOption {
  const p = telemetryPalette(el)
  const top = sessions.slice(0, limit)
  const rows = top.slice().reverse()
  const labels = rows.map((s) => {
    const rank = top.findIndex((row) => row.session_id === s.session_id) + 1
    const title = (s.title || s.session_id.slice(0, 8)).slice(0, 18)
    return `${String(rank).padStart(2, '0')} — ${title}`
  })
  const tip = glassTooltip(p)
  const axis = axisCommon(p)

  return {
    animationDuration: 800,
    animationEasing: 'cubicOut',
    tooltip: {
      ...tip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: p.glass } },
      formatter(params: unknown) {
        const items = Array.isArray(params) ? params : [params]
        const first = items[0] as { dataIndex?: number }
        const row = rows[first.dataIndex ?? 0]
        if (!row) return ''
        return [
          `<div style="opacity:.7;letter-spacing:.12em;margin-bottom:6px">SESS-${row.session_id.slice(0, 8)}</div>`,
          `${row.title}`,
          `Σ   ${row.total_tokens.toLocaleString()} tok`,
          `¥   ${row.cost_cny.toFixed(4)}`,
        ].join('<br/>')
      },
    },
    grid: { left: 12, right: 56, top: 12, bottom: 12, containLabel: true },
    xAxis: {
      type: 'value',
      ...axis,
      axisLabel: {
        ...axis.axisLabel,
        formatter: (v: number) => (v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)),
      },
      name: 'tok',
      nameTextStyle: { color: p.faint, fontFamily: p.mono, fontSize: 10 },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: p.muted, fontFamily: p.mono, fontSize: 10 },
      splitLine: { show: false },
    },
    series: [
      {
        type: 'bar',
        data: rows.map((s) => s.total_tokens),
        barWidth: 10,
        itemStyle: { color: p.mint, borderRadius: [0, 2, 2, 0] },
        label: {
          show: true,
          position: 'right',
          color: p.faint,
          fontFamily: p.mono,
          fontSize: 10,
          formatter: (params: { dataIndex?: number }) => {
            const row = rows[params.dataIndex ?? 0]
            return row ? `¥${row.cost_cny.toFixed(2)}` : ''
          },
        },
      },
    ],
  }
}
