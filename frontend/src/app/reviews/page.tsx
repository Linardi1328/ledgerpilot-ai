"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/context/AuthContext";
import { Role } from "@/types/roles";
import { ALL_SCENARIOS } from "@/lib/mock/fixtures";
import { buildLiveReviewTaskUrl } from "@/lib/api/lineage";
import { RiskBadge, StatusBadge } from "@/components/ui/Badge";
import { FileText, ArrowRight, Info, Search, AlertCircle } from "lucide-react";

export default function ReviewQueuePage() {
  const { mode, effectiveRole, connectionStatus } = useAuth();
  const [filterRisk, setFilterRisk] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  if (mode === "live" && (effectiveRole === null || connectionStatus !== "connected")) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center space-y-3">
        <div className="flex items-center justify-center space-x-2 text-amber-400 font-bold text-base">
          <AlertCircle className="w-5 h-5" />
          <span>
            {connectionStatus === "unauthenticated"
              ? "Authentication Required"
              : "Review Queue Unavailable (Backend Offline)"}
          </span>
        </div>
        <p className="text-xs text-slate-300">
          {connectionStatus === "unauthenticated"
            ? "Authentication is required to inspect the review queue."
            : "The FastAPI backend server is unreachable. Live mode has failed closed to protect accounting integrity."}
        </p>
      </div>
    );
  }

  if (effectiveRole === Role.CLIENT_SUBMITTER) {
    return (
      <div className="bg-slate-900 border border-purple-900/60 rounded-xl p-6 text-center space-y-3">
        <h2 className="font-bold text-base text-slate-100">Restricted Access</h2>
        <p className="text-xs text-slate-300">
          Client Submitters are not authorized to view the accounting review queue. Please use the Client Information Portal.
        </p>
        <Link
          href="/portal"
          className="inline-flex items-center px-4 py-2 rounded bg-purple-600 text-white text-xs font-bold"
        >
          Go to Client Portal
        </Link>
      </div>
    );
  }

  if (effectiveRole === Role.FIRM_ADMIN) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center space-y-3">
        <h2 className="font-bold text-base text-slate-100">Review Queue Unavailable to Firm Admin</h2>
        <p className="text-xs text-slate-300">
          Firm Administrators do not hold <code>VIEW_REVIEW_TASK</code> permissions under Phase 5 RBAC. Switch to Accountant or Senior Reviewer to access review worklists.
        </p>
      </div>
    );
  }

  const filteredScenarios = ALL_SCENARIOS.filter((sc) => {
    if (filterRisk !== "all" && sc.task.risk_class !== filterRisk) return false;
    if (
      searchQuery &&
      !sc.document.submitted_filename.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !sc.title.toLowerCase().includes(searchQuery.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-5">
      {/* Top Banner explaining Mock Worklist vs Live Worklist Dependency */}
      {mode === "mock" ? (
        <div className="bg-blue-950/40 border border-blue-800/80 rounded-lg p-3 text-xs text-blue-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Info className="w-4 h-4 text-blue-400 shrink-0" />
            <span>
              <strong>Demo Queue — Future Backend Worklist API</strong>: Demonstrates the multi-tenant review queue. Click any task to enter the high-density Review Workspace.
            </span>
          </div>
          <span className="text-[10px] font-mono bg-blue-900/60 text-blue-300 px-2 py-0.5 rounded">
            Mock Mode
          </span>
        </div>
      ) : (
        <div className="bg-amber-950/40 border border-amber-800/80 rounded-lg p-3 text-xs text-amber-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Info className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Operational review queue requires the review-worklist backend endpoint</strong>: In Phase 5 live mode, review tasks are scoped to known decision lineage. Launch the tasks below to test against live FastAPI endpoints.
            </span>
          </div>
          <span className="text-[10px] font-mono bg-amber-900/60 text-amber-300 px-2 py-0.5 rounded">
            Live Mode Lineage
          </span>
        </div>
      )}

      {/* Filter & Search Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <label htmlFor="riskFilter" className="text-xs text-slate-400">Filter Risk:</label>
          <select
            id="riskFilter"
            value={filterRisk}
            onChange={(e) => setFilterRisk(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All Risks ({ALL_SCENARIOS.length})</option>
            <option value="ordinary">Ordinary Only</option>
            <option value="senior_review_required">Senior Review Required</option>
            <option value="blocked">Approval Blocked</option>
          </select>
        </div>

        <div className="relative">
          <label htmlFor="queueSearchInput" className="sr-only">Search invoices</label>
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
          <input
            id="queueSearchInput"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search invoice or filename..."
            className="bg-slate-950 border border-slate-800 rounded pl-8 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 w-56"
          />
        </div>
      </div>

      {/* Review Queue Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-950 text-slate-400 text-[11px] uppercase font-mono border-b border-slate-800">
              <tr>
                <th className="py-3 px-3">Document / Scenario</th>
                <th className="py-3 px-3">Risk Classification</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Owner</th>
                <th className="py-3 px-3">Total (MYR)</th>
                <th className="py-3 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {filteredScenarios.map((sc) => {
                const url = buildLiveReviewTaskUrl(sc.lineage);

                return (
                  <tr key={sc.key} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-100 flex items-center space-x-1.5">
                        <FileText className="w-3.5 h-3.5 text-blue-400" />
                        <span>{sc.document.submitted_filename}</span>
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{sc.title}</div>
                    </td>

                    <td className="py-3 px-3">
                      <RiskBadge riskClass={sc.task.risk_class} />
                    </td>

                    <td className="py-3 px-3">
                      <StatusBadge status={sc.task.status} />
                    </td>

                    <td className="py-3 px-3 font-mono text-[11px] text-slate-400">
                      {sc.task.owner_membership_id.slice(0, 8)}...
                    </td>

                    <td className="py-3 px-3 font-mono font-semibold text-slate-100">
                      {sc.decision.proposed_journal?.total_debits || "-"}
                    </td>

                    <td className="py-3 px-3 text-right">
                      <Link
                        href={url}
                        className="inline-flex items-center space-x-1 px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition shadow"
                      >
                        <span>Review</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
