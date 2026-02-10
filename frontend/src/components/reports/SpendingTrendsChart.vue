<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SpendingTrendsEnvelope } from '@/api/reports'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import { getTooltipTransform } from '@/utils/chart'

const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const props = withDefaults(
  defineProps<{
    envelopes: SpendingTrendsEnvelope[]
    height?: number
  }>(),
  {
    height: 250,
  }
)

// Chart dimensions
const width = 600
const padding = { top: 20, right: 120, bottom: 40, left: 70 }
const chartWidth = width - padding.left - padding.right
const chartHeight = computed(() => props.height - padding.top - padding.bottom)

// Hover state
const hoveredEnvelope = ref<string | null>(null)
const hoveredPeriodIndex = ref<number | null>(null)

// Color palette for lines
const colors = ['#2196f3', '#4caf50', '#ff9800', '#e91e63', '#9c27b0', '#00bcd4', '#795548', '#607d8b']

function getColor(index: number): string {
  return colors[index % colors.length] ?? '#2196f3'
}

// Get all periods from the first envelope (they all should have same periods)
const periods = computed(() => {
  if (props.envelopes.length === 0) return []
  return (props.envelopes[0]?.periods ?? []).map((p) => p.period_start)
})

// Calculate max spending for Y scale
const maxSpending = computed(() => {
  let max = 0
  for (const env of props.envelopes) {
    for (const period of env.periods) {
      if (period.amount > max) max = period.amount
    }
  }
  return max || 10000
})

// Y bounds with padding
const yBounds = computed(() => {
  return {
    min: 0,
    max: maxSpending.value * 1.1,
  }
})

// X scale
function xScale(index: number): number {
  if (periods.value.length <= 1) return padding.left + chartWidth / 2
  return padding.left + (index / (periods.value.length - 1)) * chartWidth
}

// Y scale
function yScale(amount: number): number {
  const range = yBounds.value.max - yBounds.value.min
  if (range === 0) return padding.top + chartHeight.value / 2
  return padding.top + chartHeight.value - ((amount - yBounds.value.min) / range) * chartHeight.value
}

// Generate line path for an envelope
function getLinePath(envelope: SpendingTrendsEnvelope): string {
  if (envelope.periods.length === 0) return ''
  return envelope.periods
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p.amount)}`)
    .join(' ')
}

// Y axis ticks
const yTicks = computed(() => {
  const { min, max } = yBounds.value
  const range = max - min
  const tickCount = 5
  const ticks: number[] = []
  for (let i = 0; i < tickCount; i++) {
    ticks.push(min + (range * i) / (tickCount - 1))
  }
  return ticks.reverse()
})

// Format dollar amounts for axis
function formatAxisAmount(cents: number): string {
  const dollars = cents / 100
  if (Math.abs(dollars) >= 1000000) {
    return `$${(dollars / 1000000).toFixed(1)}M`
  } else if (Math.abs(dollars) >= 1000) {
    return `$${(dollars / 1000).toFixed(0)}K`
  }
  return `$${dollars.toFixed(0)}`
}

// Format period for x-axis (avoid timezone issues by parsing directly)
function formatPeriod(dateStr: string): string {
  const month = parseInt(dateStr.split('-')[1] ?? '1', 10)
  return monthNames[month - 1] ?? 'Jan'
}

// Format full period for tooltip
function formatFullPeriod(dateStr: string): string {
  const parts = dateStr.split('-')
  const year = parts[0] ?? ''
  const month = parts[1] ?? '1'
  return `${monthNames[parseInt(month, 10) - 1] ?? 'Jan'} ${year}`
}

// X-axis labels
const xAxisLabels = computed(() => {
  const allPeriods = periods.value
  if (allPeriods.length <= 6) {
    return allPeriods.map((p, i) => ({ label: formatPeriod(p), x: xScale(i) }))
  } else if (allPeriods.length <= 12) {
    return allPeriods
      .filter((_, i) => i % 2 === 0 || i === allPeriods.length - 1)
      .map((p) => ({
        label: formatPeriod(p),
        x: xScale(periods.value.indexOf(p)),
      }))
  } else {
    return allPeriods
      .filter((_, i) => i % 3 === 0 || i === allPeriods.length - 1)
      .map((p) => ({
        label: formatPeriod(p),
        x: xScale(periods.value.indexOf(p)),
      }))
  }
})

// Get data points for an envelope
function getDataPoints(envelope: SpendingTrendsEnvelope) {
  return envelope.periods.map((p, i) => ({
    x: xScale(i),
    y: yScale(p.amount),
    period: p,
    periodIndex: i,
  }))
}

// Check if a line should be highlighted
function isHighlighted(envelopeId: string): boolean {
  return hoveredEnvelope.value === null || hoveredEnvelope.value === envelopeId
}

// Get opacity for a line
function getLineOpacity(envelopeId: string): number {
  return isHighlighted(envelopeId) ? 1 : 0.2
}
</script>

<template>
  <div class="spending-trends-chart-container">
    <svg
      :viewBox="`0 0 ${width} ${height}`"
      class="spending-trends-chart"
      preserveAspectRatio="xMidYMid meet"
    >
      <!-- Grid lines -->
      <g class="grid-lines">
        <line
          v-for="(tick, i) in yTicks"
          :key="i"
          :x1="padding.left"
          :y1="yScale(tick)"
          :x2="width - padding.right"
          :y2="yScale(tick)"
          stroke="#e0e0e0"
          stroke-dasharray="2,2"
        />
      </g>

      <!-- Lines for each envelope -->
      <g
        v-for="(envelope, envIndex) in envelopes"
        :key="envelope.envelope_id"
        class="envelope-line"
      >
        <path
          :d="getLinePath(envelope)"
          fill="none"
          :stroke="getColor(envIndex)"
          stroke-width="2.5"
          stroke-linejoin="round"
          stroke-linecap="round"
          :opacity="getLineOpacity(envelope.envelope_id)"
          @mouseenter="hoveredEnvelope = envelope.envelope_id"
          @mouseleave="hoveredEnvelope = null"
        />
        <!-- Data points -->
        <circle
          v-for="point in getDataPoints(envelope)"
          :key="point.periodIndex"
          :cx="point.x"
          :cy="point.y"
          :r="hoveredEnvelope === envelope.envelope_id && hoveredPeriodIndex === point.periodIndex ? 6 : 4"
          :fill="getColor(envIndex)"
          stroke="white"
          stroke-width="2"
          :opacity="getLineOpacity(envelope.envelope_id)"
          class="data-point"
          @mouseenter="hoveredEnvelope = envelope.envelope_id; hoveredPeriodIndex = point.periodIndex"
          @mouseleave="hoveredEnvelope = null; hoveredPeriodIndex = null"
        />
      </g>

      <!-- Y-axis labels -->
      <g class="y-axis">
        <text
          v-for="(tick, i) in yTicks"
          :key="i"
          :x="padding.left - 8"
          :y="yScale(tick)"
          text-anchor="end"
          dominant-baseline="middle"
          class="axis-label"
        >
          {{ formatAxisAmount(tick) }}
        </text>
      </g>

      <!-- X-axis labels -->
      <g class="x-axis">
        <text
          v-for="(label, i) in xAxisLabels"
          :key="i"
          :x="label.x"
          :y="height - padding.bottom + 20"
          text-anchor="middle"
          class="axis-label"
        >
          {{ label.label }}
        </text>
      </g>

      <!-- Legend -->
      <g class="legend">
        <g
          v-for="(envelope, envIndex) in envelopes.slice(0, 6)"
          :key="envelope.envelope_id"
          :transform="`translate(${width - padding.right + 10}, ${padding.top + envIndex * 20})`"
          class="legend-item"
          @mouseenter="hoveredEnvelope = envelope.envelope_id"
          @mouseleave="hoveredEnvelope = null"
        >
          <rect
            width="12"
            height="12"
            :fill="getColor(envIndex)"
            rx="2"
          />
          <text
            x="16"
            y="10"
            class="legend-label"
          >
            {{ envelope.envelope_name.slice(0, 12) }}{{ envelope.envelope_name.length > 12 ? '...' : '' }}
          </text>
        </g>
      </g>
    </svg>

    <!-- Tooltip -->
    <div
      v-if="hoveredEnvelope !== null && hoveredPeriodIndex !== null"
      class="chart-tooltip"
      :style="{
        left: `${(xScale(hoveredPeriodIndex) / width) * 100}%`,
        top: `${
          (yScale(
            envelopes.find((e) => e.envelope_id === hoveredEnvelope)?.periods[hoveredPeriodIndex]?.amount || 0
          ) /
            height) *
          100
        }%`,
        transform: getTooltipTransform(xScale(hoveredPeriodIndex), padding.left, chartWidth),
      }"
    >
      <div class="tooltip-content">
        <div class="tooltip-title">
          {{ formatFullPeriod(periods[hoveredPeriodIndex] ?? '') }}
        </div>
        <div class="tooltip-envelope">
          {{ envelopes.find((e) => e.envelope_id === hoveredEnvelope)?.envelope_name }}
        </div>
        <div class="tooltip-row">
          <span>Spent:</span>
          <MoneyDisplay
            :amount="
              -(envelopes.find((e) => e.envelope_id === hoveredEnvelope)?.periods[hoveredPeriodIndex]?.amount || 0)
            "
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.spending-trends-chart-container {
  position: relative;
  width: 100%;
}

.spending-trends-chart {
  width: 100%;
  height: auto;
}

.axis-label {
  font-size: 11px;
  fill: #757575;
}

.legend-label {
  font-size: 10px;
  fill: #424242;
}

.legend-item {
  cursor: pointer;
}

.data-point {
  cursor: pointer;
  transition: r 0.15s ease;
}

.envelope-line path {
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.chart-tooltip {
  position: absolute;
  pointer-events: none;
  z-index: 10;
}

.tooltip-content {
  background: rgba(33, 33, 33, 0.95);
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  white-space: nowrap;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.tooltip-title {
  font-weight: 600;
  margin-bottom: 2px;
  text-align: center;
}

.tooltip-envelope {
  color: #bdbdbd;
  font-size: 11px;
  margin-bottom: 4px;
  text-align: center;
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.tooltip-row span:first-child {
  color: #bdbdbd;
}
</style>
