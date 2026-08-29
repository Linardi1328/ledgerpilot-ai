import React from "react";
import { AlertTriangle } from "lucide-react";

export function DisclaimerBanner() {
  return (
    <aside aria-label="Synthetic disclaimer" className="bg-amber-950/30 border-b border-amber-900/50 px-5 py-1.5 text-[11px] text-amber-300/90 flex flex-wrap items-center justify-between gap-2">
      <div className="flex items-center space-x-2">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span>
          <strong>Synthetic Accounting & Tax Configuration</strong>: Rules, tax codes (<code>SYN-TAX-06</code>), and proposed journals are synthetic development demo configurations. Malaysian SST and accounting treatment require practitioner validation before production use.
        </span>
      </div>
      <div className="text-[10px] font-mono text-amber-400/80">
        AI Assists • Human Review Authoritative
      </div>
    </aside>
  );
}
