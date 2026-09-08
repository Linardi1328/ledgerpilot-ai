"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Role } from "@/types/roles";
import { useAuth } from "@/lib/context/AuthContext";
import {
  AlertCircle,
  FileText,
  Inbox,
  Landmark,
  Settings,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const { effectiveRole, mode, connectionStatus } = useAuth();

  const isActive = (path: string) => {
    if (path === "/" && pathname === "/") return true;
    if (path !== "/" && pathname?.startsWith(path)) return true;
    return false;
  };

  if (mode === "live" && (effectiveRole === null || connectionStatus !== "connected")) {
    return (
      <nav
        className="bg-slate-950/70 border-b border-slate-800 px-5 py-2.5 flex items-center space-x-3 text-xs"
        aria-label="Disconnected Navigation"
      >
        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
        <span className="text-slate-400">
          {connectionStatus === "unauthenticated"
            ? "Authentication required. Review navigation is locked until credentials are authenticated."
            : "Backend offline. Live mode failed closed — no synthetic authority active."}
        </span>
      </nav>
    );
  }

  if (effectiveRole === Role.CLIENT_SUBMITTER) {
    return (
      <nav
        className="bg-slate-950/70 border-b border-slate-800 px-5 flex items-center space-x-6 text-xs font-medium"
        aria-label="Submitter Navigation"
      >
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

  if (effectiveRole === Role.FIRM_ADMIN) {
    return (
      <nav
        className="bg-slate-950/70 border-b border-slate-800 px-5 flex items-center space-x-6 text-xs font-medium"
        aria-label="Admin Navigation"
      >
        <div className="py-2.5 border-b-2 border-slate-500 text-slate-300 flex items-center space-x-2">
          <Settings className="w-3.5 h-3.5" />
          <span>Firm Administration (Accounting Decision Access Not Granted)</span>
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

  return (
    <nav
      className="bg-slate-950/70 border-b border-slate-800 px-5 flex items-center space-x-6 text-xs font-medium overflow-x-auto"
      aria-label="Reviewer Navigation"
    >
      <Link
        href="/reviews"
        className={`py-2.5 border-b-2 flex items-center space-x-2 transition shrink-0 ${
          isActive("/reviews")
            ? "border-blue-500 text-blue-400 font-semibold"
            : "border-transparent text-slate-400 hover:text-slate-200"
        }`}
      >
        <FileText className="w-3.5 h-3.5" />
        <span>Review Queue</span>
      </Link>

      <Link
        href="/reconciliation"
        className={`py-2.5 border-b-2 flex items-center space-x-2 transition shrink-0 ${
          isActive("/reconciliation")
            ? "border-blue-500 text-blue-400 font-semibold"
            : "border-transparent text-slate-400 hover:text-slate-200"
        }`}
      >
        <Landmark className="w-3.5 h-3.5" />
        <span>Bank Reconciliation</span>
        <span className="bg-blue-900/60 text-blue-300 text-[10px] px-1.5 py-0.2 rounded-full font-mono">
          Phase 6
        </span>
      </Link>

      <Link
        href="/intake"
        className={`py-2.5 border-b-2 flex items-center space-x-2 transition shrink-0 ${
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
        className={`py-2.5 border-b-2 flex items-center space-x-2 transition shrink-0 ${
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
