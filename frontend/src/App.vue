<script setup>
import { ref, computed, onMounted, onBeforeUnmount, h } from 'vue'
import {
  NConfigProvider, NGlobalStyle, darkTheme, NCard, NDataTable,
  NGrid, NGi, NStatistic, NTag, NSpace, NAlert, NText,
} from 'naive-ui'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const status = ref(null)
const rows = ref([])
const history = ref([])
const selected = ref('BTC/USDT')
const error = ref('')

const pct = (v, d = 4) => (v === null || v === undefined ? '-' : (v * 100).toFixed(d) + '%')

async function load() {
  try {
    const [s, r, hs] = await Promise.all([
      fetch('/api/status').then((x) => x.json()),
      fetch('/api/spreads').then((x) => x.json()),
      fetch('/api/history?symbol=' + encodeURIComponent(selected.value)).then((x) => x.json()),
    ])
    status.value = s
    rows.value = r
    history.value = hs
    error.value = ''
  } catch (e) {
    error.value = '连不上后端（127.0.0.1:8100），请确认 “crypto-arb Backend” 窗口还在运行'
  }
}

let timer
onMounted(() => {
  load()
  timer = setInterval(load, 3000)
})
onBeforeUnmount(() => clearInterval(timer))

const columns = [
  { title: '交易对', key: 'symbol' },
  { title: '买入所', key: 'buy' },
  { title: '卖出所', key: 'sell' },
  { title: '买入价 ask', key: 'ask' },
  { title: '卖出价 bid', key: 'bid' },
  { title: '毛价差', key: 'gross', render: (r) => pct(r.gross) },
  { title: '成本', key: 'cost', render: (r) => pct(r.cost, 3) },
  {
    title: '净价差',
    key: 'net',
    render: (r) =>
      h(NTag, { type: r.net > 0 ? 'success' : 'error', bordered: false }, { default: () => pct(r.net) }),
  },
  { title: '本次最大毛价差', key: 'max_gross', render: (r) => pct(r.max_gross) },
  { title: '正毛价差占比', key: 'pos_ratio', render: (r) => (r.pos_ratio * 100).toFixed(1) + '%' },
]

const rowProps = (r) => ({
  style: 'cursor: pointer',
  onClick: () => {
    selected.value = r.symbol
    load()
  },
})

const runMinutes = computed(() => {
  if (!status.value) return '-'
  const start = new Date(status.value.started_at.replace(' ', 'T'))
  return Math.floor((Date.now() - start.getTime()) / 60000) + ' 分钟'
})

const fmt = (v) => (typeof v === 'number' ? v.toFixed(4) + '%' : v)
const chartOption = computed(() => ({
  tooltip: { trigger: 'axis', valueFormatter: fmt },
  legend: { data: ['毛价差', '净价差'], textStyle: { color: '#ccc' } },
  grid: { left: 70, right: 20, top: 40, bottom: 30 },
  xAxis: { type: 'category', data: history.value.map((p) => p.t) },
  yAxis: { type: 'value', axisLabel: { formatter: (v) => v.toFixed(3) + '%' } },
  series: [
    { name: '毛价差', type: 'line', showSymbol: false, data: history.value.map((p) => p.gross * 100) },
    { name: '净价差', type: 'line', showSymbol: false, data: history.value.map((p) => p.net * 100) },
  ],
}))
</script>

<template>
  <n-config-provider :theme="darkTheme">
    <n-global-style />
    <div style="padding: 20px; max-width: 1400px; margin: 0 auto">
      <n-space justify="space-between" align="center" style="margin-bottom: 16px">
        <h2 style="margin: 0">crypto-arb 跨所价差仪表盘</h2>
        <n-space v-if="status">
          <n-tag v-for="(st, ex) in status.exchanges" :key="ex" :type="st === 'ok' ? 'success' : 'error'">
            {{ ex }} {{ st === 'ok' ? '在线' : '失败' }}
          </n-tag>
        </n-space>
      </n-space>

      <n-alert v-if="error" type="error" style="margin-bottom: 16px">{{ error }}</n-alert>

      <n-grid :cols="4" :x-gap="12" style="margin-bottom: 16px">
        <n-gi><n-card><n-statistic label="已运行" :value="runMinutes" /></n-card></n-gi>
        <n-gi><n-card><n-statistic label="扫描轮数" :value="status ? status.rounds : '-'" /></n-card></n-gi>
        <n-gi>
          <n-card>
            <n-statistic label="每轮耗时" :value="status && status.round_seconds ? status.round_seconds + ' 秒' : '-'" />
          </n-card>
        </n-gi>
        <n-gi><n-card><n-statistic label="取价失败次数" :value="status ? status.fail_count : '-'" /></n-card></n-gi>
      </n-grid>

      <n-card title="最新一轮（每个交易对只显示净价差最高的方向，点击行查看走势）" style="margin-bottom: 16px">
        <n-data-table :columns="columns" :data="rows" :row-key="(r) => r.symbol" :row-props="rowProps" size="small" />
      </n-card>

      <n-card :title="selected + ' 价差走势'">
        <v-chart :option="chartOption" autoresize style="height: 340px" />
      </n-card>

      <n-text v-if="status" depth="3" style="display: block; margin-top: 12px; font-size: 12px">
        参数：滑点缓冲 {{ (status.params.slippage * 100).toFixed(2) }}% ｜ 扫描间隔 {{ status.params.interval_sec }} 秒 ｜
        最后更新 {{ status.last_round_at || '-' }} ｜ 明细 {{ status.log_path }}
      </n-text>
    </div>
  </n-config-provider>
</template>
