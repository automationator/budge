<script setup lang="ts">
import { computed, ref } from 'vue'
import type { NetWorthPeriod } from '@/api/reports'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import { getTooltipTransform } from '@/utils/chart'

const props = withDefaults(
  defineProps<{
    periods: NetWorthPeriod[]
    height?: number
  }>(),
  {
    height: 200,
  }
)

// Chart dimensions
const width = 600
const padding = { top: 20, right: 20, bottom: 40, left: 70 }
const chartWidth = width - padding.left - padding.right
const chartHeight = computed(() => props.height - padding.top - padding.bottom)

// Hover state
const hoveredIndex = ref<number | null>(null)

// Calculate min/max for Y axis
const yBounds = computed(() => {
  if (props.periods.length === 0) return { min: 0, max: 100 }
  const values = props.periods.map((p) => p.net_worth)
  const min = Math.min(...values)
  const max = Math.max(...values)
  // Add 10% padding
  const range = max - min || Math.abs(max) || 10000
  return {
    min: min - range * 0.1,
    max: max + range * 0.1,
  }
})

// X scale: map period index to x position
function xScale(index: number): number {
  if (props.periods.length <= 1) return padding.left + chartWidth / 2
  return padding.left + (index / (props.periods.length - 1)) * chartWidth
}

// Y scale: map amount to y position (inverted - larger values = smaller y)
function yScale(amount: number): number {
  const range = yBounds.value.max - yBounds.value.min
  if (range === 0) return padding.top + chartHeight.value / 2
  return padding.top + chartHeight.value - ((amount - yBounds.value.min) / range) * chartHeight.value
}

// Generate SVG path for the line
const linePath = computed(() => {
  if (props.periods.length === 0) return ''
  return props.periods
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p.net_worth)}`)
    .join(' ')
})

// Generate SVG path for the area fill
const areaPath = computed(() => {
  if (props.periods.length === 0) return ''
  const zeroY = yScale(0)
  const points = props.periods.map((p, i) => `${xScale(i)} ${yScale(p.net_worth)}`).join(' L ')
  return `M ${xScale(0)} ${zeroY} L ${points} L ${xScale(props.periods.length - 1)} ${zeroY} Z`
})

// Data points for circles
const dataPoints = computed(() => {
  return props.periods.map((p, i) => ({
    x: xScale(i),
    y: yScale(p.net_worth),
    period: p,
    index: i,
  }))
})

// Y axis tick marks
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

// Month names for date formatting
const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Format month for x-axis (avoid timezone issues by parsing directly)
function formatMonth(dateStr: string): string {
  const month = parseInt(dateStr.split('-')[1] ?? '1', 10)
  return monthNames[month - 1] ?? 'Jan'
}

// Format full month/year for tooltip (avoid timezone issues by parsing directly)
function formatFullMonth(dateStr: string): string {
  const parts = dateStr.split('-').map(Number)
  const year = parts[0] ?? 0
  const month = parts[1] ?? 1
  return `${monthNames[month - 1] ?? 'Jan'} ${year}`
}

// Get color based on value
function getLineColor(netWorth: number): string {
  return netWorth >= 0 ? '#4caf50' : '#f44336'
}

// Get most common color for the line
const primaryLineColor = computed(() => {
  if (props.periods.length === 0) return '#4caf50'
  const positiveCount = props.periods.filter((p) => p.net_worth >= 0).length
  return positiveCount >= props.periods.length / 2 ? '#4caf50' : '#f44336'
})

// Determine which x-axis labels to show (avoid overcrowding)
const xAxisLabels = computed(() => {
  const periods = props.periods
  if (periods.length <= 6) {
    // Show all labels
    return periods.map((p, i) => ({ label: formatMonth(p.period_start), x: xScale(i) }))
  } else if (periods.length <= 12) {
    // Show every other
    return periods
      .filter((_, i) => i % 2 === 0 || i === periods.length - 1)
      .map((p) => ({
        label: formatMonth(p.period_start),
        x: xScale(props.periods.indexOf(p)),
      }))
  } else {
    // Show quarterly
    return periods
      .filter((_, i) => i % 3 === 0 || i === periods.length - 1)
      .map((p) => ({
        label: formatMonth(p.period_start),
        x: xScale(props.periods.indexOf(p)),
      }))
  }
})

// Zero line y position
const zeroLineY = computed(() => yScale(0))
</script>

<template>
  <div class="net-worth-chart-container">
    <svg
      :viewBox="`0 0 ${width} ${height}`"
      class="net-worth-chart"
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

      <!-- Zero line (if visible in range) -->
      <line
        v-if="yBounds.min < 0 && yBounds.max > 0"
        :x1="padding.left"
        :y1="zeroLineY"
        :x2="width - padding.right"
        :y2="zeroLineY"
        stroke="#9e9e9e"
        stroke-width="1"
      />

      <!-- Area fill under line -->
      <path
        v-if="periods.length > 0"
        :d="areaPath"
        :fill="primaryLineColor"
        fill-opacity="0.1"
      />

      <!-- Net worth line -->
      <path
        v-if="periods.length > 0"
        :d="linePath"
        fill="none"
        :stroke="primaryLineColor"
        stroke-width="2.5"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

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

      <!-- Data points (circles) -->
      <g class="data-points">
        <circle
          v-for="point in dataPoints"
          :key="point.index"
          :cx="point.x"
          :cy="point.y"
          :r="hoveredIndex === point.index ? 6 : 4"
          :fill="getLineColor(point.period.net_worth)"
          stroke="white"
          stroke-width="2"
          class="data-point"
          @mouseenter="hoveredIndex = point.index"
          @mouseleave="hoveredIndex = null"
        />
      </g>

      <!-- Invisible larger hit areas for better tooltip interaction -->
      <g class="hit-areas">
        <circle
          v-for="point in dataPoints"
          :key="point.index"
          :cx="point.x"
          :cy="point.y"
          r="15"
          fill="transparent"
          @mouseenter="hoveredIndex = point.index"
          @mouseleave="hoveredIndex = null"
        />
      </g>
    </svg>

    <!-- Tooltip -->
    <div
      v-if="hoveredIndex !== null && dataPoints[hoveredIndex]"
      class="chart-tooltip"
      :style="{
        left: `${((dataPoints[hoveredIndex]?.x ?? 0) / width) * 100}%`,
        top: `${((dataPoints[hoveredIndex]?.y ?? 0) / height) * 100}%`,
        transform: getTooltipTransform(dataPoints[hoveredIndex]?.x ?? 0, padding.left, chartWidth),
      }"
    >
      <div class="tooltip-content">
        <div class="tooltip-title">
          {{ formatFullMonth(dataPoints[hoveredIndex]?.period.period_start ?? '') }}
        </div>
        <div class="tooltip-row">
          <span>Net Worth:</span>
          <MoneyDisplay
            :amount="dataPoints[hoveredIndex]?.period.net_worth ?? 0"
            :class="(dataPoints[hoveredIndex]?.period.net_worth ?? 0) >= 0 ? 'text-success' : 'text-error'"
          />
        </div>
        <div class="tooltip-row text-caption">
          <span>Assets:</span>
          <MoneyDisplay
            :amount="dataPoints[hoveredIndex]?.period.total_assets ?? 0"
            class="text-success"
          />
        </div>
        <div class="tooltip-row text-caption">
          <span>Liabilities:</span>
          <MoneyDisplay
            :amount="-(dataPoints[hoveredIndex]?.period.total_liabilities ?? 0)"
            class="text-error"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.net-worth-chart-container {
  position: relative;
  width: 100%;
}

.net-worth-chart {
  width: 100%;
  height: auto;
}

.axis-label {
  font-size: 11px;
  fill: #757575;
}

.data-point {
  cursor: pointer;
  transition: r 0.15s ease;
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

.text-success {
  color: #4caf50;
}

.text-error {
  color: #f44336;
}
</style>
