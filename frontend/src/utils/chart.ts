/**
 * Get tooltip CSS transform based on horizontal position to prevent overflow.
 * - Left edge (0-25%): Tooltip shifts right
 * - Center (25-75%): Tooltip centered
 * - Right edge (75-100%): Tooltip shifts left
 */
export function getTooltipTransform(
  x: number,
  paddingLeft: number,
  chartWidth: number
): string {
  const position = (x - paddingLeft) / chartWidth

  if (position < 0.25) {
    return 'translate(-20%, -100%) translateY(-12px)'
  } else if (position > 0.75) {
    return 'translate(-80%, -100%) translateY(-12px)'
  }
  return 'translate(-50%, -100%) translateY(-12px)'
}
