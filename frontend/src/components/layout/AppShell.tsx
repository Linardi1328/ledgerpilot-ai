"use client";

import React from "react";
import Link from "next/link";
import { Header } from "./Header";
import { Navbar } from "./Navbar";
import { DisclaimerBanner } from "./DisclaimerBanner";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased">
      <Header />
      <Navbar />
      <DisclaimerBanner />
      <main id="main-content" className="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto">{children}</main>
      <footer className="bg-slate-950 border-t border-slate-800/80 px-6 py-4 text-center text-xs text-slate-500 font-mono space-y-2">
        <p>LedgerPilot AI • Phase 5 Human Review Workflow • AI recommendations assist the accountant; an authorised human owns the decision.</p>
        <nav aria-label="Legal policies" className="flex flex-wrap justify-center gap-x-4 gap-y-2">
          <Link className="text-slate-300 underline underline-offset-4 hover:text-white" href="/privacy">Privacy</Link>
          <Link className="text-slate-300 underline underline-offset-4 hover:text-white" href="/terms">Terms</Link>
          <Link className="text-slate-300 underline underline-offset-4 hover:text-white" href="/cookies">Cookies</Link>
          <Link className="text-slate-300 underline underline-offset-4 hover:text-white" href="/refunds">Payments & refunds</Link>
        </nav>
      </footer>
    </div>
  );
}
