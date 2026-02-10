import { describe, it, expect } from 'vitest'
import { formatDateRange } from '@/utils/date'

describe('formatDateRange', () => {
  it('formats same month range', () => {
    // Jan 1 - Jan 31 (exclusive end: Feb 1)
    expect(formatDateRange('2026-01-01', '2026-02-01')).toBe('Jan 1 - 31, 2026')
  })

  it('formats same year different months range', () => {
    // Jan 1 - Mar 31 (exclusive end: Apr 1)
    expect(formatDateRange('2026-01-01', '2026-04-01')).toBe('Jan 1 - Mar 31, 2026')
  })

  it('formats cross-year range', () => {
    // Dec 1, 2025 - Jan 31, 2026 (exclusive end: Feb 1)
    expect(formatDateRange('2025-12-01', '2026-02-01')).toBe('Dec 1, 2025 - Jan 31, 2026')
  })

  it('formats quarterly range Q1', () => {
    // Jan 1 - Mar 31 (exclusive end: Apr 1)
    expect(formatDateRange('2026-01-01', '2026-04-01')).toBe('Jan 1 - Mar 31, 2026')
  })

  it('formats quarterly range Q4', () => {
    // Oct 1 - Dec 31 (exclusive end: Jan 1 next year)
    // After subtracting 1 day, end becomes Dec 31, 2025 - same year as start
    expect(formatDateRange('2025-10-01', '2026-01-01')).toBe('Oct 1 - Dec 31, 2025')
  })

  it('formats weekly range', () => {
    // Mon Jan 6 - Sun Jan 12 (exclusive end: Jan 13)
    expect(formatDateRange('2025-01-06', '2025-01-13')).toBe('Jan 6 - 12, 2025')
  })

  it('formats yearly range', () => {
    // Jan 1 - Dec 31 (exclusive end: Jan 1 next year)
    expect(formatDateRange('2025-01-01', '2026-01-01')).toBe('Jan 1 - Dec 31, 2025')
  })
})
