/**
 * Extract the local date as YYYY-MM-DD string.
 *
 * Unlike `toISOString().split('T')[0]`, this uses local time,
 * so it won't shift to "tomorrow" when it's late evening in
 * a timezone behind UTC.
 */
export function toLocaleDateString(date: Date = new Date()): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Format a date range for display.
 *
 * Converts exclusive end date to inclusive for display.
 * Handles same-month, same-year, and cross-year formatting.
 *
 * @param startDate - ISO date string (YYYY-MM-DD)
 * @param endDate - ISO date string (YYYY-MM-DD), exclusive
 * @returns Formatted date range string
 *
 * Examples:
 * - Same month: "Jan 1 - 31, 2026"
 * - Same year: "Jan 1 - Mar 31, 2026"
 * - Cross-year: "Dec 1, 2025 - Jan 31, 2026"
 */
export function formatDateRange(startDate: string, endDate: string): string {
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

  // Parse start date
  const startParts = startDate.split('-').map(Number)
  const startYear = startParts[0] ?? 0
  const startMonth = startParts[1] ?? 1
  const startDay = startParts[2] ?? 1

  // Parse end date and subtract one day to make it inclusive
  // Use UTC to avoid timezone issues
  const endParts = endDate.split('-').map(Number)
  const endYearParsed = endParts[0] ?? 0
  const endMonthParsed = endParts[1] ?? 1
  const endDayParsed = endParts[2] ?? 1
  const endDateObj = new Date(Date.UTC(endYearParsed, endMonthParsed - 1, endDayParsed))
  endDateObj.setUTCDate(endDateObj.getUTCDate() - 1)
  const endYear = endDateObj.getUTCFullYear()
  const endMonth = endDateObj.getUTCMonth() // 0-indexed
  const endDay = endDateObj.getUTCDate()

  const startMonthIdx = startMonth - 1 // Convert to 0-indexed

  // Same month and year
  if (startYear === endYear && startMonthIdx === endMonth) {
    return `${monthNames[startMonthIdx]} ${startDay} - ${endDay}, ${startYear}`
  }

  // Same year, different months
  if (startYear === endYear) {
    return `${monthNames[startMonthIdx]} ${startDay} - ${monthNames[endMonth]} ${endDay}, ${startYear}`
  }

  // Different years
  return `${monthNames[startMonthIdx]} ${startDay}, ${startYear} - ${monthNames[endMonth]} ${endDay}, ${endYear}`
}
