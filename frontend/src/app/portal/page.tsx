"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/lib/context/AuthContext";
import { Role } from "@/types/roles";
import { ALL_SCENARIOS } from "@/lib/mock/fixtures";
import { buildLivePortalUrl } from "@/lib/api/lineage";
import { FileText, ArrowRight, Inbox, HelpCircle, AlertCircle } from "lucide-react";

export default function ClientPortalIndex() {
  const { effectiveRole, mode, connectionStatus } = useAuth();

  if (mode === "live" && (effectiveRole === null || connectionStatus !== "connected")) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center space-y-3 max-w-xl mx-auto">
        <div className="flex items-center justify-center space-x-2 text-amber-400 font-bold text-base">
          <AlertCircle className="w-5 h-5" />
          <span>Client Portal Unavailable (Backend Offline)</span>
        </div>
        <p className="text-xs text-slate-300">
          The FastAPI backend server is unreachable. Live mode has failed closed.
        </p>
      </div>
    );
  }

  if (effectiveRole !== Role.CLIENT_SUBMITTER) {
    return (
      <div className="bg-slate-900 border border-purple-900/60 rounded-xl p-8 text-center space-y-4 max-w-xl mx-auto shadow-2xl">
        <div className="w-12 h-12 rounded-full bg-purple-950 border border-purple-800 flex items-center justify-center mx-auto text-purple-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="font-bold text-base text-slate-100">Restricted Submitter Access</h2>
        <p className="text-xs text-slate-300 leading-relaxed">
          Your current verified role is not authorized to access the Client Information Portal. This view is strictly isolated to authenticated <strong>Client Submitter</strong> principals.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="bg-slate-900 border border-purple-900/60 rounded-xl p-6 space-y-3 shadow-xl">
        <div className="flex items-center space-x-2 text-purple-400 font-bold text-base">
          <Inbox className="w-5 h-5" />
          <span>Client Information Requests</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          When your accounting team needs clarification on an uploaded invoice or receipt, the request appears below. Select a document to view the inquiry and provide a clarification.
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <span className="font-bold text-xs text-slate-200">Pending Requests</span>
          <span className="text-[10px] font-mono text-slate-400">Phase 5 Canonical Portals</span>
        </div>

        <div className="space-y-3">
          {ALL_SCENARIOS.map((sc) => {
            const portalUrl = buildLivePortalUrl(sc.lineage);

            return (
              <div
                key={sc.key}
                className="bg-slate-950 p-4 rounded-lg border border-slate-800 flex flex-wrap items-center justify-between gap-3"
              >
                <div className="flex items-center space-x-3">
                  <div className="p-2 rounded bg-purple-950/60 text-purple-400 border border-purple-800">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="font-semibold text-xs text-slate-200">
                      {sc.document.submitted_filename}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      Task: {sc.lineage.reviewTaskId.slice(0, 8)}...
                    </div>
                  </div>
                </div>

                <Link
                  href={portalUrl}
                  className="inline-flex items-center space-x-1 px-3.5 py-1.5 rounded bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold transition"
                >
                  <HelpCircle className="w-3.5 h-3.5" />
                  <span>Open Inquiry</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
