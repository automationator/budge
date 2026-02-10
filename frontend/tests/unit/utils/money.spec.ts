import { describe, it, expect } from 'vitest'
import {
  formatMoney,
  formatMoneyCompact,
  parseMoney,
  getMoneyColor,
  formatMoneySigned,
} from '@/utils/money'

describe('money utilities', () => {
  describe('formatMoney', () => {
    it('formats positive cents to currency', () => {
      expect(formatMoney(12345)).toBe('$123.45')
    })

    it('formats negative cents to currency', () => {
      expect(formatMoney(-12345)).toBe('-$123.45')
    })

    it('formats zero', () => {
      expect(formatMoney(0)).toBe('$0.00')
    })

    it('formats small amounts', () => {
      expect(formatMoney(1)).toBe('$0.01')
      expect(formatMoney(99)).toBe('$0.99')
      expect(formatMoney(100)).toBe('$1.00')
    })

    it('handles large amounts with commas', () => {
      expect(formatMoney(1234567890)).toBe('$12,345,678.90')
    })

    it('applies custom options', () => {
      const result = formatMoney(12345, { minimumFractionDigits: 0 })
      expect(result).toBe('$123.45')
    })
  })

  describe('formatMoneyCompact', () => {
    it('returns standard format for small amounts', () => {
      expect(formatMoneyCompact(999999)).toBe('$9,999.99')
    })

    it('formats thousands compactly', () => {
      const result = formatMoneyCompact(1500000) // $15,000
      // Intl compact notation varies by locale, accept reasonable formats
      expect(result).toMatch(/\$15\.?0?K|\$15,000/)
    })

    it('formats millions compactly', () => {
      const result = formatMoneyCompact(150000000) // $1,500,000
      expect(result).toMatch(/\$1\.5M|\$1,500K/)
    })

    it('handles negative amounts', () => {
      const result = formatMoneyCompact(-1500000)
      expect(result).toMatch(/-?\$15\.?0?K|-\$15,000/)
    })

    it('returns standard format below threshold', () => {
      expect(formatMoneyCompact(500000)).toBe('$5,000.00')
    })
  })

  describe('parseMoney', () => {
    it('parses simple dollar string to cents', () => {
      expect(parseMoney('123.45')).toBe(12345)
    })

    it('handles currency symbol', () => {
      expect(parseMoney('$123.45')).toBe(12345)
    })

    it('handles commas in large numbers', () => {
      expect(parseMoney('$1,234.56')).toBe(123456)
    })

    it('handles spaces around the value', () => {
      expect(parseMoney(' $ 123.45 ')).toBe(12345)
    })

    it('returns 0 for invalid input', () => {
      expect(parseMoney('invalid')).toBe(0)
      expect(parseMoney('')).toBe(0)
      expect(parseMoney('abc')).toBe(0)
    })

    it('rounds to nearest cent', () => {
      expect(parseMoney('123.456')).toBe(12346)
      expect(parseMoney('123.454')).toBe(12345)
    })

    it('handles negative values', () => {
      expect(parseMoney('-123.45')).toBe(-12345)
    })

    it('handles whole dollar amounts', () => {
      expect(parseMoney('100')).toBe(10000)
    })

    it('handles amounts with one decimal place', () => {
      expect(parseMoney('10.5')).toBe(1050)
    })
  })

  describe('getMoneyColor', () => {
    it('returns success for positive amounts', () => {
      expect(getMoneyColor(100)).toBe('text-success')
      expect(getMoneyColor(1)).toBe('text-success')
    })

    it('returns error for negative amounts', () => {
      expect(getMoneyColor(-100)).toBe('text-error')
      expect(getMoneyColor(-1)).toBe('text-error')
    })

    it('returns empty string for zero', () => {
      expect(getMoneyColor(0)).toBe('')
    })
  })

  describe('formatMoneySigned', () => {
    it('adds plus sign for positive amounts', () => {
      expect(formatMoneySigned(12345)).toBe('+$123.45')
    })

    it('adds minus sign for negative amounts', () => {
      expect(formatMoneySigned(-12345)).toBe('-$123.45')
    })

    it('no sign for zero', () => {
      expect(formatMoneySigned(0)).toBe('$0.00')
    })

    it('handles small positive amounts', () => {
      expect(formatMoneySigned(1)).toBe('+$0.01')
    })

    it('handles small negative amounts', () => {
      expect(formatMoneySigned(-1)).toBe('-$0.01')
    })
  })
})
