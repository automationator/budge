<script setup lang="ts">
import { computed, ref } from 'vue'
import type { EnvelopeBalanceHistoryItem, AccountBalanceHistoryItem } from '@/api/reports'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import { getTooltipTransform } from '@/utils/chart'

const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const props = withDefaults(
  defineProps<{
    items: EnvelopeBalanceHistoryItem[] | AccountBalanceHistoryItem[]
    height?: number
    targetBalance?: number | null // Optional target line for envelopes
    title?: string
  }>(),
  {
    height: 200,
    targetBalance: null,
    title: 'Balance History',
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
  if (props.items.length === 0) return { min: 0, max: 100 }
  const values = props.items.map((p) => p.balance)
  // Include target balance in the range if provided
  if (props.targetBalance !== null) {
    values.push(props.targetBalance)
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  // Add 10% padding
  const range = max - min || Math.abs(max) || 10000
  return {
    min: min - range * 0.1,
    max: max + range * 0.1,
  }
})

// X scale: map index to x position
function xScale(index: number): number {
  if (props.items.length <= 1) return padding.left + chartWidth / 2
  return padding.left + (index / (props.items.length - 1)) * chartWidth
}

// Y scale: map amount to y position (inverted)
function yScale(amount: number): number {
  const range = yBounds.value.max - yBounds.value.min
  if (range === 0) return padding.top + chartHeight.value / 2
  return padding.top + chartHeight.value - ((amount - yBounds.value.min) / range) * chartHeight.value
}

// Generate SVG path for the line
const linePath = computed(() => {
  if (props.items.length === 0) return ''
  return props.items
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p.balance)}`)
    .join(' ')
})

// Generate SVG path for the area fill
const areaPath = computed(() => {
  if (props.items.length === 0) return ''
  const zeroY = yScale(0)
  const points = props.items.map((p, i) => `${xScale(i)} ${yScale(p.balance)}`).join(' L ')
  return `M ${xScale(0)} ${zeroY} L ${points} L ${xScale(props.items.length - 1)} ${zeroY} Z`
})

// Data points for circles
const dataPoints = computed(() => {
  return props.items.map((p, i) => ({
    x: xScale(i),
    y: yScale(p.balance),
    item: p,
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

// Format date for x-axis (avoid timezone issues by parsing directly)
function formatDate(dateStr: string): string {
  const parts = dateStr.split('-')
  const month = parts[1] ?? '01'
  const day = parts[2] ?? '01'
  return `${monthNames[parseInt(month, 10) - 1]} ${parseInt(day, 10)}`
}

// Format full date for tooltip
function formatFullDate(dateStr: string): string {
  const parts = dateStr.split('-')
  const year = parts[0] ?? ''
  const month = parts[1] ?? '01'
  const day = parts[2] ?? '01'
  return `${monthNames[parseInt(month, 10) - 1]} ${parseInt(day, 10)}, ${year}`
}

// Get color based on value
function getLineColor(balance: number): string {
  return balance >= 0 ? '#4caf50' : '#f44336'
}

// Primary line color (based on most common value sign)
const primaryLineColor = computed(() => {
  if (props.items.length === 0) return '#4caf50'
  const positiveCount = props.items.filter((p) => p.balance >= 0).length
  return positiveCount >= props.items.length / 2 ? '#4caf50' : '#f44336'
})

// X-axis labels (sample to avoid crowding)
const xAxisLabels = computed(() => {
  const items = props.items
  if (items.length <= 7) {
    return items.map((p, i) => ({ label: formatDate(p.date), x: xScale(i) }))
  } else if (items.length <= 30) {
    // Show every week
    return items
      .filter((_, i) => i % 7 === 0 || i === items.length - 1)
      .map((p) => ({
        label: formatDate(p.date),
        x: xScale(props.items.indexOf(p)),
      }))
  } else {
    // Show monthly
    return items
      .filter((_, i) => i % 30 === 0 || i === items.length - 1)
      .map((p) => ({
        label: formatDate(p.date),
        x: xScale(props.items.indexOf(p)),
      }))
  }
})

// Zero line y position
const zeroLineY = computed(() => yScale(0))

// Target line y position
const targetLineY = computed(() => (props.targetBalance !== null ? yScale(props.targetBalance) : null))
</script>

<template>
  <div class="balance-history-chart-container">
    <svg
      :viewBox="`0 0 ${width} ${height}`"
      class="balance-history-chart"
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

      <!-- Target line (if provided) -->
      <line
        v-if="targetLineY !== null"
        :x1="padding.left"
        :y1="targetLineY"
        :x2="width - padding.right"
        :y2="targetLineY"
        stroke="#2196f3"
        stroke-width="2"
        stroke-dasharray="5,5"
      />
      <text
        v-if="targetLineY !== null"
        :x="width - padding.right - 5"
        :y="targetLineY - 5"
        text-anchor="end"
        class="target-label"
      >
        Target
      </text>

      <!-- Area fill under line -->
      <path
        v-if="items.length > 0"
        :d="areaPath"
        :fill="primaryLineColor"
        fill-opacity="0.1"
      />

      <!-- Balance line -->
      <path
        v-if="items.length > 0"
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
          :fill="getLineColor(point.item.balance)"
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
          {{ formatFullDate(dataPoints[hoveredIndex]?.item.date ?? '') }}
        </div>
        <div class="tooltip-row">
          <span>Balance:</span>
          <MoneyDisplay
            :amount="dataPoints[hoveredIndex]?.item.balance ?? 0"
            :class="(dataPoints[hoveredIndex]?.item.balance ?? 0) >= 0 ? 'text-success' : 'text-error'"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.balance-history-chart-container {
  position: relative;
  width: 100%;
}

.balance-history-chart {
  width: 100%;
  height: auto;
}

.axis-label {
  font-size: 11px;
  fill: #757575;
}

.target-label {
  font-size: 10px;
  fill: #2196f3;
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
