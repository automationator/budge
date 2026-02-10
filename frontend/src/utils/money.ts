/**
 * Format cents as a currency string
 */
export function formatMoney(cents: number, options?: Intl.NumberFormatOptions): string {
  const dollars = cents / 100
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    ...options,
  }).format(dollars)
}

/**
 * Format cents as a compact currency string (e.g., $1.2K)
 */
export function formatMoneyCompact(cents: number): string {
  const dollars = cents / 100
  if (Math.abs(dollars) >= 1000000) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(dollars)
  }
  if (Math.abs(dollars) >= 10000) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(dollars)
  }
  return formatMoney(cents)
}

/**
 * Parse a dollar string to cents
 */
export function parseMoney(value: string): number {
  // Remove currency symbols, commas, spaces
  const cleaned = value.replace(/[$,\s]/g, '')
  const dollars = parseFloat(cleaned)
  if (isNaN(dollars)) return 0
  return Math.round(dollars * 100)
}

/**
 * Get the appropriate color class for a money amount
 */
export function getMoneyColor(cents: number): string {
  if (cents > 0) return 'text-success'
  if (cents < 0) return 'text-error'
  return ''
}

/**
 * Format cents as a signed string (+$10.00 or -$10.00)
 */
export function formatMoneySigned(cents: number): string {
  const formatted = formatMoney(Math.abs(cents))
  if (cents > 0) return `+${formatted}`
  if (cents < 0) return `-${formatted}`
  return formatted
}
