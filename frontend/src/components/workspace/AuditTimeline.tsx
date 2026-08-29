import React, { useState } from "react";
import { ReviewAuditEventResponse } from "@/types/api";
import { ShieldCheck, ChevronDown, ChevronRight } from "lucide-react";

export function AuditTimeline({
  events,
}: {
  events: ReviewAuditEventResponse[];
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3 text-slate-100">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <span className="font-semibold text-xs text-slate-200 flex items-center space-x-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
          <span>Task Audit Log</span>
        </span>
        <span className="text-[10px] font-mono text-slate-500">Append-Only Event Stream</span>
      </div>

      <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
        {events.length === 0 ? (
          <div className="text-xs text-slate-500 italic p-3 text-center bg-slate-950/60 rounded border border-slate-800">
            No audit events recorded.
          </div>
        ) : (
          events.map((event) => {
            const isExpanded = expandedId === event.id;
            const hasMetadata = Object.keys(event.metadata || {}).length > 0;

            return (
              <div
                key={event.id}
                className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs space-y-1 font-mono"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-purple-300 text-[11px]">{event.event_type}</span>
                  <span className="text-[10px] text-slate-500">
                    {new Date(event.occurred_at).toUTCString().slice(17, 25)} UTC
                  </span>
                </div>

                <div className="text-[10px] text-slate-400 flex items-center justify-between">
                  <span>Actor: {event.actor_user_id ? `User ${event.actor_user_id.slice(0, 8)}` : "System"}</span>
                  {event.request_id && <span className="text-slate-600">{event.request_id}</span>}
                </div>

                {hasMetadata && (
                  <div>
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : event.id)}
                      className="text-[10px] text-slate-400 hover:text-slate-200 flex items-center space-x-1 pt-1"
                    >
                      {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                      <span>{isExpanded ? "Hide Metadata" : "Inspect Metadata"}</span>
                    </button>

                    {isExpanded && (
                      <pre className="mt-1 p-2 bg-slate-900 rounded border border-slate-800 text-[10px] text-slate-300 overflow-x-auto">
                        {JSON.stringify(event.metadata, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
