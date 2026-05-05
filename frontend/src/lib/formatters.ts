/**
 * Hebrew number/currency/date formatters for Israeli real estate.
 */

export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "-";
  // Preserve up to 2 decimals when the value has them; otherwise show as
  // an integer. Bank-statement amounts (e.g. 1,500.45) stay precise while
  // round budget figures stay clean.
  const rounded = Math.round(value * 100) / 100;
  const hasDecimals = rounded % 1 !== 0;
  const formatted = rounded.toLocaleString("he-IL", {
    minimumFractionDigits: hasDecimals ? 2 : 0,
    maximumFractionDigits: 2,
  });
  return `${formatted} ₪`;
}

export function formatCurrencyShort(value: number | null | undefined): string {
  if (value == null) return "-";
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M ₪`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${Math.round(value / 1_000).toLocaleString("he-IL")}K ₪`;
  }
  return formatCurrency(value);
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "-";
  return `${value.toFixed(1)}%`;
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null) return "-";
  return Math.round(value).toLocaleString("he-IL");
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleDateString("he-IL", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function formatMonthYear(dateStr: string): string {
  const d = new Date(dateStr);
  const months = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
  ];
  return `${months[d.getMonth()]} ${d.getFullYear()}`;
}
