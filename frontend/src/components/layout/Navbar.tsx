"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Role } from "@/types/roles";
import { useAuth } from "@/lib/context/AuthContext";
import { FileText, Inbox, ShieldCheck, UploadCloud, Settings } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const { role } = useAuth();

  const isActive = (path: string) => {
    if (path === "/" && pathname === "/") return true;
    if (path !== "/" && pathname?.startsWith(path)) return true;
    return false;
  };

  // 1. Client Submitter: STRICT ISOLATION to portal
  if (role === Role.CLIENT_SUBMITTER) {
    return (
      <nav className="bg-slate-950/70 border-b border-slate-800 px-5 flex items-center space-x-6 text-xs font-medium" aria-label="Submitter Navigation">
        <Link
          href="/portal"
          className={`py-2.5 border-b-2 flex items-center space-x-2 transition ${
            isActive("/portal")
              ? "border-purple-500 text-purple-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Inbox className="w-3.5 h-3.5" />
          <span>Client Information Portal</span>
          <span className="bg-purple-900/60 text-purple-300 text-[10px] px-1.5 py-0.2 rounded-full font-mono">
            Active
          </span>
        </Link>

        <Link
          href="/intake"
          className={`py-2.5 border-b-2 flex items-center space-x-2 transition ${
            isActive("/intake")
              ? "border-purple-500 text-purple-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <UploadCloud className="w-3.5 h-3.5" />
          <span>Document Intake</span>
        </Link>
      </nav>
    );
  }

  // 2. Firm Administrator: Shows workspace admin scope (no accounting review authority)
  if (role === Role.FIRM_ADMIN) {
    return (
      <nav className="bg-slate-950/70 border-b border-slate-800 px-5 flex items-center space-x-6 text-xs font-medium" aria-label="Admin Navigation">
        <div className="py-2.5 border-b-2 border-slate-500 text-slate-300 flex items-center space-x-2">
          <Settings className="w-3.5 h-3.5" />
          <span>Firm Administration (Phase 5 Review Access Not Granted)</span>
        </div>
        <Link
          href="/audit"
          className={`py-2.5 border-b-2 flex items-center space-x-2 transition ${
            isActive("/audit")
              ? "border-blue-500 text-blue-400 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Audit Log</span>
        </Link>
      </nav>
    );
  }

  // 3. Reviewers (Accountant, Senior Reviewer, Auditor)
  return (
    <nav className="bg-slate-950/70 border-b border-slate-800 px-5 flex items-center space-x-6 text-xs font-medium" aria-label="Reviewer Navigation">
      <Link
        href="/reviews"
        className={`py-2.5 border-b-2 flex items-center space-x-2 transition ${
          isActive("/reviews")
            ? "border-blue-500 text-blue-400 font-semibold"
            : "border-transparent text-slate-400 hover:text-slate-200"
        }`}
      >
        <FileText className="w-3.5 h-3.5" />
        <span>Review Queue</span>
        <span className="bg-blue-900/60 text-blue-300 text-[10px] px-1.5 py-0.2 rounded-full font-mono">
          Worklist
        </span>
      </Link>

      <Link
        href="/intake"
        className={`py-2.5 border-b-2 flex items-center space-x-2 transition ${
          isActive("/intake")
            ? "border-blue-500 text-blue-400 font-semibold"
            : "border-transparent text-slate-400 hover:text-slate-200"
        }`}
      >
        <UploadCloud className="w-3.5 h-3.5" />
        <span>Document Intake Pipeline</span>
      </Link>

      <Link
        href="/audit"
        className={`py-2.5 border-b-2 flex items-center space-x-2 transition ${
          isActive("/audit")
            ? "border-blue-500 text-blue-400 font-semibold"
            : "border-transparent text-slate-400 hover:text-slate-200"
        }`}
      >
        <ShieldCheck className="w-3.5 h-3.5" />
        <span>Audit Stream</span>
      </Link>
    </nav>
  );
}
