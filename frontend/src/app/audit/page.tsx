"use client";

import React from "react";
import { useAuth } from "@/lib/context/AuthContext";
import { ALL_SCENARIOS } from "@/lib/mock/fixtures";
import { ShieldCheck, Info } from "lucide-react";

export default function AuditStreamPage() {
  const { mode } = useAuth();

  // In mock mode, gather all audit events across synthetic scenarios
  const allEvents = ALL_SCENARIOS.flatMap((s) =>
    s.history.audit_events.map((e) => ({
      ...e,
      documentName: s.document.submitted_filename,
    }))
  );

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-3 shadow-xl">
        <div className="flex items-center space-x-2 text-purple-400 font-bold text-base">
          <ShieldCheck className="w-5 h-5" />
          <span>Audit Stream & Traceability</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          LedgerPilot AI maintains an append-only audit trail of every review event, escalation, comment, and outcome authorization.
        </p>
      </div>

      {mode === "live" && (
        <div className="bg-amber-950/40 border border-amber-800/80 rounded-lg p-4 text-xs text-amber-200 flex items-start space-x-3">
          <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <strong>Task-Scoped Audit Lineage Active</strong>
            <p className="text-[11px] text-slate-300">
              In Phase 5, audit events are queried per review task via <code>GET /api/v1/.../review-tasks/&#123;id&#125;/history</code>. A global cross-task firm audit stream is a future administrative API endpoint.
            </p>
          </div>
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <span className="font-bold text-xs text-slate-200">Recent Audit Events</span>
          <span className="text-[10px] font-mono text-slate-400">Append-Only Event Records</span>
        </div>

        <div className="space-y-2.5">
          {allEvents.map((evt) => (
            <div
              key={evt.id}
              className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5 font-mono text-slate-300"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-purple-300">{evt.event_type}</span>
                <span className="text-[10px] text-slate-500">
                  {new Date(evt.occurred_at).toUTCString()}
                </span>
              </div>

              <div className="text-[11px] text-slate-400 font-sans flex items-center justify-between">
                <span>Doc: {evt.documentName}</span>
                <span className="font-mono text-[10px] text-slate-500">
                  Actor: {evt.actor_user_id ? evt.actor_user_id.slice(0, 8) : "System"}
                </span>
              </div>

              {evt.metadata && Object.keys(evt.metadata).length > 0 && (
                <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-900">
                  Metadata: {JSON.stringify(evt.metadata)}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
