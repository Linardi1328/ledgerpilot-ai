"use client";

import React from "react";
import { Header } from "./Header";
import { Navbar } from "./Navbar";
import { DisclaimerBanner } from "./DisclaimerBanner";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased">
      <Header />
      <Navbar />
      <DisclaimerBanner />
      <main className="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto">{children}</main>
      <footer className="bg-slate-950 border-t border-slate-800/80 px-6 py-3 text-center text-xs text-slate-500 font-mono">
        LedgerPilot AI • Phase 5 Human Review Workflow • AI Recommendations assist the accountant; an authorised human owns the decision.
      </footer>
    </div>
  );
}
