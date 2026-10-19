const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

/** Format a number as US dollars, e.g. $1,234.56. */
export function money(value: number): string {
  return usd.format(value);
}

/** Format a price with two decimals and no currency sign. */
export function price(value: number): string {
  return value.toFixed(2);
}

/** Format a percent value (already in percent units) with a sign, e.g. +1.23%. */
export function percent(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

/** Format a dollar change with a sign, e.g. +$12.00 / -$3.50. */
export function signedMoney(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${usd.format(Math.abs(value))}`;
}

/** Format a share quantity, trimming trailing zeros for fractional shares. */
export function shares(value: number): string {
  return Number(value.toFixed(4)).toString();
}
