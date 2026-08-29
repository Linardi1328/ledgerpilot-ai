/**
 * Monetary Arithmetic & Exact Decimal Utilities for LedgerPilot AI
 *
 * Implements strict non-floating-point arithmetic for financial numbers.
 * Converts decimal strings into scaled BigInt values (4 decimal places: 10,000 scale)
 * matching PostgreSQL Numeric(18,4).
 */

const SCALE_DECIMALS = 4;
const SCALE_FACTOR = 10_000n;

export interface MonetaryVerificationResult {
  isBalanced: boolean;
  totalDebits: string;
  totalCredits: string;
  variance: string;
  isPositive: boolean;
}

/**
 * Parses a decimal string (e.g. "1250.00", "0.75", "-10.50") into a scaled BigInt without Float conversion.
 */
export function parseDecimalToScaledBigInt(decimalStr: string | null | undefined): bigint {
  if (!decimalStr || typeof decimalStr !== "string") {
    return 0n;
  }

  const trimmed = decimalStr.trim();
  if (trimmed === "" || trimmed === "-") {
    return 0n;
  }

  const isNegative = trimmed.startsWith("-");
  const cleanStr = isNegative ? trimmed.slice(1) : trimmed;

  const parts = cleanStr.split(".");
  if (parts.length > 2) {
    throw new Error(`Invalid decimal format: ${decimalStr}`);
  }

  const integerPart = parts[0] || "0";
  let fractionPart = parts[1] || "";

  // Pad or slice fraction part to exactly SCALE_DECIMALS (4)
  if (fractionPart.length < SCALE_DECIMALS) {
    fractionPart = fractionPart.padEnd(SCALE_DECIMALS, "0");
  } else if (fractionPart.length > SCALE_DECIMALS) {
    fractionPart = fractionPart.slice(0, SCALE_DECIMALS);
  }

  const integerBigInt = BigInt(integerPart);
  const fractionBigInt = BigInt(fractionPart);
  const totalScaled = integerBigInt * SCALE_FACTOR + fractionBigInt;

  return isNegative ? -totalScaled : totalScaled;
}

/**
 * Formats a scaled BigInt back to a formatted 2 or 4 decimal place string.
 */
export function formatScaledBigIntToDecimal(scaled: bigint, displayDecimals = 2): string {
  const isNegative = scaled < 0n;
  const absScaled = isNegative ? -scaled : scaled;

  const integerVal = absScaled / SCALE_FACTOR;
  const fractionVal = absScaled % SCALE_FACTOR;

  let fractionStr = fractionVal.toString().padStart(SCALE_DECIMALS, "0");
  if (displayDecimals < SCALE_DECIMALS) {
    fractionStr = fractionStr.slice(0, displayDecimals);
  }

  const sign = isNegative ? "-" : "";
  return `${sign}${integerVal.toString()}.${fractionStr}`;
}

/**
 * Formats a decimal string into a standard display string with commas and fixed 2 decimal places.
 * E.g. "1250.00" -> "1,250.00" without floating point coercion.
 */
export function formatMoney(
  amount: string | null | undefined,
  currency = "MYR",
  includeCurrency = true
): string {
  if (!amount || amount.trim() === "" || amount === "-") {
    return includeCurrency ? `${currency} 0.00` : "0.00";
  }

  try {
    const scaled = parseDecimalToScaledBigInt(amount);
    const isNegative = scaled < 0n;
    const absScaled = isNegative ? -scaled : scaled;

    const integerPart = (absScaled / SCALE_FACTOR).toString();
    const fractionPart = (absScaled % SCALE_FACTOR).toString().padStart(SCALE_DECIMALS, "0").slice(0, 2);

    // Format thousands with commas
    const withCommas = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    const sign = isNegative ? "-" : "";
    const formatted = `${sign}${withCommas}.${fractionPart}`;

    return includeCurrency ? `${currency} ${formatted}` : formatted;
  } catch {
    return includeCurrency ? `${currency} ${amount}` : amount;
  }
}

/**
 * Performs diagnostic double-entry balance verification on a list of journal lines.
 * Returns exact decimal totals, balance status, and variance.
 */
export function verifyJournalBalance(
  lines: Array<{ debit_amount?: string | null; credit_amount?: string | null }>
): MonetaryVerificationResult {
  let totalDebitsScaled = 0n;
  let totalCreditsScaled = 0n;

  for (const line of lines) {
    if (line.debit_amount && line.debit_amount !== "-") {
      totalDebitsScaled += parseDecimalToScaledBigInt(line.debit_amount);
    }
    if (line.credit_amount && line.credit_amount !== "-") {
      totalCreditsScaled += parseDecimalToScaledBigInt(line.credit_amount);
    }
  }

  const isBalanced = totalDebitsScaled === totalCreditsScaled;
  const varianceScaled = totalDebitsScaled - totalCreditsScaled;
  const absVariance = varianceScaled < 0n ? -varianceScaled : varianceScaled;

  return {
    isBalanced,
    totalDebits: formatScaledBigIntToDecimal(totalDebitsScaled, 2),
    totalCredits: formatScaledBigIntToDecimal(totalCreditsScaled, 2),
    variance: formatScaledBigIntToDecimal(absVariance, 2),
    isPositive: totalDebitsScaled > 0n && totalCreditsScaled > 0n,
  };
}
