"use client";

import React from "react";
import { Role } from "@/types/roles";
import { useAuth } from "@/lib/context/AuthContext";
import { useClientContext } from "@/lib/context/ClientContext";

export function Header() {
  const { mode, setMode, role, setRole, connectionStatus } = useAuth();
  const { activeFirm, activeClient, availableClients, setActiveClientId } = useClientContext();

  const getStatusBadge = () => {
    switch (connectionStatus) {
      case "connected":
        return (
          <span className="inline-flex items-center space-x-1.5 text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 px-2.5 py-1 rounded-full font-mono text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>FastAPI Connected</span>
          </span>
        );
      case "connecting":
        return (
          <span className="inline-flex items-center space-x-1.5 text-xs text-blue-400 bg-blue-950/40 border border-blue-800/60 px-2.5 py-1 rounded-full font-mono text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-spin" />
            <span>Connecting...</span>
          </span>
        );
      case "unauthenticated":
        return (
          <span className="inline-flex items-center space-x-1.5 text-xs text-amber-400 bg-amber-950/40 border border-amber-800/60 px-2.5 py-1 rounded-full font-mono text-[11px]">
            <span>⚠️ Auth Required</span>
          </span>
        );
      case "unavailable":
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 text-xs text-rose-400 bg-rose-950/40 border border-rose-800/60 px-2.5 py-1 rounded-full font-mono text-[11px]">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
            <span>Backend Offline (Mock Active)</span>
          </span>
        );
    }
  };

  return (
    <header className="bg-slate-950 border-b border-slate-800 px-5 py-3 flex flex-wrap items-center justify-between gap-3 text-slate-100">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className="w-7 h-7 rounded bg-blue-600 flex items-center justify-center font-bold text-white text-sm">
            LP
          </div>
          <span className="font-bold text-base tracking-tight text-white">LedgerPilot AI</span>
          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
            Phase 5
          </span>
        </div>

        <div className="h-4 w-px bg-slate-800 hidden sm:block" />

        {/* Firm & Client Context */}
        <div className="hidden md:flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-1.5">
            <span className="text-slate-400">Firm:</span>
            <span className="font-medium text-slate-200 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              {activeFirm.name}
            </span>
          </div>

          <div className="flex items-center space-x-1.5">
            <label htmlFor="clientSelect" className="text-slate-400">Client:</label>
            <select
              id="clientSelect"
              value={activeClient.id}
              onChange={(e) => setActiveClientId(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded px-2 py-0.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {availableClients.map((client) => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Role & Mode Switcher Controls */}
      <div className="flex items-center space-x-3">
        {/* Mode Toggle (Mock vs Live) */}
        <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs font-mono">
          <button
            onClick={() => setMode("mock")}
            className={`px-2 py-1 rounded text-[11px] font-medium transition ${
              mode === "mock" ? "bg-slate-700 text-white font-semibold" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Mock Demo
          </button>
          <button
            onClick={() => setMode("live")}
            className={`px-2 py-1 rounded text-[11px] font-medium transition ${
              mode === "live" ? "bg-blue-600 text-white font-semibold" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Live API
          </button>
        </div>

        {/* Principal Role Simulator */}
        <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs">
          <span className="text-slate-400 px-1 text-[11px] hidden sm:inline">Role:</span>
          <button
            onClick={() => setRole(Role.ACCOUNTANT)}
            className={`px-2 py-1 rounded font-medium text-[11px] transition ${
              role === Role.ACCOUNTANT ? "bg-blue-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            🧑‍💼 Accountant
          </button>
          <button
            onClick={() => setRole(Role.SENIOR_REVIEWER)}
            className={`px-2 py-1 rounded font-medium text-[11px] transition ${
              role === Role.SENIOR_REVIEWER ? "bg-amber-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            🎖️ Senior
          </button>
          <button
            onClick={() => setRole(Role.CLIENT_SUBMITTER)}
            className={`px-2 py-1 rounded font-medium text-[11px] transition ${
              role === Role.CLIENT_SUBMITTER ? "bg-purple-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            👤 Submitter
          </button>
          <button
            onClick={() => setRole(Role.AUDITOR)}
            className={`px-2 py-1 rounded font-medium text-[11px] transition ${
              role === Role.AUDITOR ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            📋 Auditor
          </button>
          <button
            onClick={() => setRole(Role.FIRM_ADMIN)}
            className={`px-2 py-1 rounded font-medium text-[11px] transition ${
              role === Role.FIRM_ADMIN ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            ⚙️ Admin
          </button>
        </div>

        {/* Backend Status Indicator */}
        <div className="hidden lg:block">{getStatusBadge()}</div>
      </div>
    </header>
  );
}
