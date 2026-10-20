export function formatPrice(n?: number): string {
  if (n === undefined) return "--";
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatPct(n?: number): string {
  if (n === undefined) return "--";
  const text = Math.abs(n).toFixed(2);
  if (Number(text) === 0) return "0.00%";
  return (n > 0 ? "+" : "-") + text + "%";
}

export function formatQty(n?: number): string {
  if (n === undefined) return "--";
  return n.toLocaleString("en-US", { maximumFractionDigits: 4 });
}

export function formatSignedMoney(n?: number): string {
  if (n === undefined) return "--";
  const text = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (Number(text.replace(/,/g, "")) === 0) return "$0.00";
  return (n > 0 ? "+$" : "-$") + text;
}
