/** INR crores display for heuristic forecasts / twin prices. */
export function formatInrCr(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(Number(value))) return '₹ —';
  const cr = Number(value) / 1e7;
  return `₹ ${cr.toFixed(digits)} Cr`;
}

export const HEURISTIC_DISCLAIMER = 'Heuristic estimate (not a trained model)';
