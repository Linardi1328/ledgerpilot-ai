"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/lib/context/AuthContext";
import { Role } from "@/types/roles";
import { ALL_SCENARIOS } from "@/lib/mock/fixtures";
import { buildLivePortalUrl, buildLiveReviewTaskUrl } from "@/lib/api/lineage";
import { FileText, Inbox, ShieldCheck, UploadCloud, ArrowRight } from "lucide-react";
import { RiskBadge, StatusBadge } from "@/components/ui/Badge";

export default function HomePage() {
  const { role } = useAuth();

  if (role === Role.CLIENT_SUBMITTER) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto">
        <div className="bg-slate-900 border border-purple-900/60 rounded-xl p-6 space-y-3 shadow-xl">
          <div className="flex items-center space-x-2 text-purple-400 font-bold text-lg">
            <Inbox className="w-5 h-5" />
            <span>Client Information Portal</span>
          </div>
          <p className="text-xs text-slate-300">
            Welcome to the Client Submitter Portal. Here you can inspect inquiries raised by your accounting team and submit requested clarifications for your invoices.
          </p>
          <div className="pt-2">
            <Link
              href="/portal"
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition"
            >
              <span>Open Client Inquiries</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (role === Role.FIRM_ADMIN) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-3 shadow-xl">
          <h2 className="font-bold text-base text-slate-100">Firm Administration</h2>
          <p className="text-xs text-slate-300">
            Current Phase 5 backend does not grant Firm Admin the <code>VIEW_REVIEW_TASK</code> or <code>VIEW_REVIEW_HISTORY</code> permissions. To review accounting tasks or authorize journals, switch your active development role to <strong>Accountant</strong> or <strong>Senior Reviewer</strong> using the role switcher above.
          </p>
          <div className="pt-2">
            <Link
              href="/audit"
              className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
            >
              <ShieldCheck className="w-4 h-4 text-blue-400" />
              <span>Inspect Audit Stream</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-3 shadow-xl">
        <div className="flex items-center justify-between">
          <h1 className="font-bold text-lg text-white">LedgerPilot AI — Human Review Workspace</h1>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
            Phase 5
          </span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">
          Welcome to the attributable human review interface. AI recommendations and deterministic accounting engine findings are presented for practitioner review. An authorised accountant or senior reviewer validates and approves the proposed double-entry journals.
        </p>

        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            href="/reviews"
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition shadow"
          >
            <FileText className="w-4 h-4" />
            <span>Open Review Queue</span>
          </Link>
          <Link
            href="/intake"
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
          >
            <UploadCloud className="w-4 h-4 text-blue-400" />
            <span>Intake Pipeline</span>
          </Link>
          <Link
            href="/audit"
            className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
          >
            <ShieldCheck className="w-4 h-4 text-purple-400" />
            <span>Audit Stream</span>
          </Link>
        </div>
      </div>

      {/* Quick Launch Scenario Worklist */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div>
            <h2 className="font-bold text-sm text-slate-100">Direct Scenario Launchers (Canonical Lineage)</h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Launch directly into fully formed Phase 5 review task workspaces with complete source lineage.
            </p>
          </div>
          <span className="text-[10px] font-mono text-slate-500">3 Synthetic Scenarios</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {ALL_SCENARIOS.map((sc) => {
            const url = buildLiveReviewTaskUrl(sc.lineage);

            return (
              <div
                key={sc.key}
                className="bg-slate-950 p-4 rounded-lg border border-slate-800 space-y-2.5 flex flex-col justify-between"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <RiskBadge riskClass={sc.task.risk_class} />
                    <StatusBadge status={sc.task.status} />
                  </div>
                  <div className="font-bold text-xs text-slate-200 pt-1">{sc.title}</div>
                  <div className="text-[11px] text-slate-400 font-mono">
                    Doc: {sc.document.submitted_filename}
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800/80">
                  <Link
                    href={url}
                    className="w-full inline-flex items-center justify-center space-x-1 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition"
                  >
                    <span>Launch Workspace</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
