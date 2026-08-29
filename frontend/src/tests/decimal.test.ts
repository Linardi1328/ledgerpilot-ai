import { describe, it, expect } from "vitest";
import {
  formatMoney,
  formatScaledBigIntToDecimal,
  parseDecimalToScaledBigInt,
  verifyJournalBalance,
} from "../lib/decimal/money";

describe("Monetary Arithmetic & Exact Decimal Utilities", () => {
  it("parses valid decimal strings into scaled BigInt values", () => {
    expect(parseDecimalToScaledBigInt("100.00")).toBe(1_000_000n);
    expect(parseDecimalToScaledBigInt("0.75")).toBe(7_500n);
    expect(parseDecimalToScaledBigInt("1234.5678")).toBe(12_345_678n);
    expect(parseDecimalToScaledBigInt("0")).toBe(0n);
    expect(parseDecimalToScaledBigInt("-50.25")).toBe(-502_500n);
  });

  it("handles trailing and missing decimals cleanly", () => {
    expect(parseDecimalToScaledBigInt("100")).toBe(1_000_000n);
    expect(parseDecimalToScaledBigInt("100.5")).toBe(1_005_000n);
    expect(parseDecimalToScaledBigInt("")).toBe(0n);
    expect(parseDecimalToScaledBigInt(null)).toBe(0n);
    expect(parseDecimalToScaledBigInt(undefined)).toBe(0n);
  });

  it("formats scaled BigInt back to exact decimal string", () => {
    expect(formatScaledBigIntToDecimal(1_000_000n, 2)).toBe("100.00");
    expect(formatScaledBigIntToDecimal(7_500n, 2)).toBe("0.75");
    expect(formatScaledBigIntToDecimal(-502_500n, 2)).toBe("-50.25");
    expect(formatScaledBigIntToDecimal(12_345_678n, 4)).toBe("1234.5678");
  });

  it("formats money with currency and thousands separators without float conversion", () => {
    expect(formatMoney("1250.00", "MYR")).toBe("MYR 1,250.00");
    expect(formatMoney("1000000.50", "MYR")).toBe("MYR 1,000,000.50");
    expect(formatMoney("0.00", "MYR")).toBe("MYR 0.00");
    expect(formatMoney("1250.00", "MYR", false)).toBe("1,250.00");
  });

  it("verifies double-entry balanced journals exactly", () => {
    const lines = [
      { debit_amount: "1179.25", credit_amount: "0.00" },
      { debit_amount: "70.75", credit_amount: "0.00" },
      { debit_amount: "0.00", credit_amount: "1250.00" },
    ];
    const result = verifyJournalBalance(lines);
    expect(result.isBalanced).toBe(true);
    expect(result.totalDebits).toBe("1250.00");
    expect(result.totalCredits).toBe("1250.00");
    expect(result.variance).toBe("0.00");
  });

  it("detects unbalanced journals and computes exact variance", () => {
    const lines = [
      { debit_amount: "3500.00", credit_amount: "0.00" },
      { debit_amount: "0.00", credit_amount: "3490.00" },
    ];
    const result = verifyJournalBalance(lines);
    expect(result.isBalanced).toBe(false);
    expect(result.totalDebits).toBe("3500.00");
    expect(result.totalCredits).toBe("3490.00");
    expect(result.variance).toBe("10.00");
  });

  it("handles high precision and large scaled monetary values", () => {
    const lines = [
      { debit_amount: "999999999.99", credit_amount: "0.00" },
      { debit_amount: "0.01", credit_amount: "0.00" },
      { debit_amount: "0.00", credit_amount: "1000000000.00" },
    ];
    const result = verifyJournalBalance(lines);
    expect(result.isBalanced).toBe(true);
    expect(result.totalDebits).toBe("1000000000.00");
    expect(result.totalCredits).toBe("1000000000.00");
  });
});
