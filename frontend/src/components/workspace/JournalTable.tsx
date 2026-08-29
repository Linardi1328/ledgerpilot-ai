import React from "react";
import { ProposedJournalResponse } from "@/types/api";
import { formatMoney, verifyJournalBalance } from "@/lib/decimal/money";
import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

export function JournalTable({
  journal,
}: {
  journal: ProposedJournalResponse | null | undefined;
}) {
  if (!journal) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 text-center text-xs text-slate-400">
        No proposed double-entry journal available for this accounting decision.
      </div>
    );
  }

  // Diagnostic independent verification
  const verification = verifyJournalBalance(journal.lines);
  const isMismatch = verification.isBalanced !== journal.is_balanced;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3 text-slate-100">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="font-semibold text-xs text-slate-200 flex items-center space-x-2">
          <span>📑 Proposed Double-Entry Journal</span>
          <span className="text-[10px] font-mono text-slate-400">(Currency: {journal.currency})</span>
        </div>

        <div>
          {journal.is_balanced ? (
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-950 border border-emerald-800 text-emerald-300">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>BALANCED (Server Authoritative)</span>
            </span>
          ) : (
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-rose-950 border border-rose-800 text-rose-300">
              <XCircle className="w-3.5 h-3.5" />
              <span>UNBALANCED (Approval Blocked)</span>
            </span>
          )}
        </div>
      </div>

      {/* Diagnostic Mismatch Warning if local calculation disagrees */}
      {isMismatch && (
        <div className="bg-amber-950/60 border border-amber-800 p-3 rounded text-xs text-amber-200 flex items-start space-x-2">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <strong className="font-bold">Journal verification mismatch</strong>
            <p className="text-[11px] mt-0.5">
              The locally displayed totals do not match the server accounting-control result. Refresh the accounting decision before continuing.
            </p>
          </div>
        </div>
      )}

      {/* Unbalanced Warning Banner */}
      {!journal.is_balanced && (
        <div className="bg-rose-950/50 border border-rose-800/80 rounded p-3 text-xs text-rose-200 space-y-1">
          <div className="font-bold flex items-center space-x-1.5">
            <XCircle className="w-4 h-4 text-rose-400" />
            <span>Deterministic Control Failure: Unbalanced Proposed Journal</span>
          </div>
          <p className="text-[11px] text-rose-300/90">
            Total debits ({formatMoney(journal.total_debits, journal.currency, false)}) do not equal total credits ({formatMoney(journal.total_credits, journal.currency, false)}). Server-authoritative deterministic controls prohibit approval of unbalanced entries.
          </p>
        </div>
      )}

      {/* Journal Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead className="bg-slate-950 text-slate-400 text-[11px] uppercase font-mono border-b border-slate-800">
            <tr>
              <th className="py-2 px-2.5 w-8">Ln</th>
              <th className="py-2 px-2.5">Account Reference</th>
              <th className="py-2 px-2.5">Explanation</th>
              <th className="py-2 px-2.5 text-right">Debit ({journal.currency})</th>
              <th className="py-2 px-2.5 text-right">Credit ({journal.currency})</th>
              <th className="py-2 px-2.5 text-center w-20">Tax Code</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 font-mono text-slate-300">
            {journal.lines.map((line) => (
              <tr key={line.id} className="hover:bg-slate-800/30 transition">
                <td className="py-2 px-2.5 text-slate-500 font-medium">{line.line_number}</td>
                <td className="py-2 px-2.5 text-slate-200 font-semibold">{line.account_reference}</td>
                <td className="py-2 px-2.5 text-slate-400 text-[11px]">{line.explanation}</td>
                <td className="py-2 px-2.5 text-right text-slate-100 tabular-nums">
                  {line.debit_amount !== "0.00" && line.debit_amount !== "0.0000"
                    ? formatMoney(line.debit_amount, journal.currency, false)
                    : "-"}
                </td>
                <td className="py-2 px-2.5 text-right text-slate-100 tabular-nums">
                  {line.credit_amount !== "0.00" && line.credit_amount !== "0.0000"
                    ? formatMoney(line.credit_amount, journal.currency, false)
                    : "-"}
                </td>
                <td className="py-2 px-2.5 text-center text-slate-400 text-[11px]">
                  {line.tax_code_reference ? (
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 text-[10px]">
                      {line.tax_code_reference}
                    </span>
                  ) : (
                    "-"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t-2 border-slate-800 font-mono font-bold text-xs bg-slate-950/70">
            <tr>
              <td colSpan={3} className="py-2.5 px-2.5 text-slate-400 uppercase text-[11px]">
                Server Authoritative Totals
              </td>
              <td
                className={`py-2.5 px-2.5 text-right tabular-nums ${
                  journal.is_balanced ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {formatMoney(journal.total_debits, journal.currency, false)}
              </td>
              <td
                className={`py-2.5 px-2.5 text-right tabular-nums ${
                  journal.is_balanced ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {formatMoney(journal.total_credits, journal.currency, false)}
              </td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
