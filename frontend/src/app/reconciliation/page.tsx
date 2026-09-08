"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Banknote,
  CheckCircle,
  History,
  Lock,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Shield,
  XCircle,
} from "lucide-react";
import { useAuth } from "@/lib/context/AuthContext";
import { useClientContext } from "@/lib/context/ClientContext";
import {
  approveReconciliationMatch,
  createReconciliationReview,
  disputeReconciliationReview,
  generateReconciliationMatch,
  getReconciliationHistory,
  listReconciliationCandidates,
  listReconciliationWorklist,
  markReconciliationUnmatched,
  reopenReconciliationReview,
  selectReconciliationCandidate,
} from "@/lib/api/reconciliation";
import { mockReconciliationStore } from "@/lib/mock/reconciliation";
import {
  canApproveReconciliation,
  canDisputeReconciliation,
  canGenerateCandidates,
  canMarkReconciliationUnmatched,
  canReopenReconciliation,
  canSelectReconciliationCandidate,
  canStartReconciliationReview,
  canViewReconciliationWorkspace,
  isReconciliationTerminal,
  reconciliationPrincipalForMode,
} from "@/lib/policy/reconciliation-policy";
import {
  ReconciliationCandidateResponse,
  ReconciliationReviewHistoryResponse,
  ReconciliationWorkflowState,
  ReconciliationWorklistItemResponse,
} from "@/types/reconciliation";

const FILTERS: Array<{ value: "all" | ReconciliationWorkflowState; label: string }> = [
  { value: "all", label: "All" },
  { value: "not_evaluated", label: "Not Evaluated" },
  { value: "unmatched", label: "Unmatched" },
  { value: "candidates_available", label: "Candidates" },
  { value: "in_review", label: "In Review" },
  { value: "disputed", label: "Disputed" },
  { value: "matched", label: "Matched" },
  { value: "resolved_unmatched", label: "Resolved Unmatched" },
];

function workflowLabel(state: ReconciliationWorkflowState): string {
  return FILTERS.find((entry) => entry.value === state)?.label ?? state;
}

function workflowClass(state: ReconciliationWorkflowState): string {
  switch (state) {
    case "matched":
      return "border-emerald-800 bg-emerald-950/50 text-emerald-300";
    case "resolved_unmatched":
      return "border-slate-700 bg-slate-800 text-slate-300";
    case "disputed":
      return "border-rose-800 bg-rose-950/50 text-rose-300";
    case "in_review":
      return "border-amber-800 bg-amber-950/50 text-amber-300";
    case "candidates_available":
      return "border-blue-800 bg-blue-950/50 text-blue-300";
    case "unmatched":
      return "border-orange-800 bg-orange-950/50 text-orange-300";
    default:
      return "border-slate-700 bg-slate-950 text-slate-400";
  }
}

function shortId(value: string | null | undefined): string {
  return value ? `${value.slice(0, 8)}…` : "—";
}

function displayDate(value: string): string {
  return new Date(value).toLocaleString("en-MY", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function ReconciliationPage() {
  const {
    mode,
    effectivePrincipal,
    effectiveRole,
    connectionStatus,
    devSubject,
    firmId,
  } = useAuth();
  const { activeClient } = useClientContext();
  const principal = useMemo(
    () => reconciliationPrincipalForMode(effectivePrincipal, mode),
    [effectivePrincipal, mode]
  );
  const [filter, setFilter] = useState<"all" | ReconciliationWorkflowState>("all");
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<ReconciliationWorklistItemResponse[]>([]);
  const [selectedTransactionId, setSelectedTransactionId] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<ReconciliationCandidateResponse[]>([]);
  const [history, setHistory] = useState<ReconciliationReviewHistoryResponse | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const hasClientAccess = Boolean(
    principal?.authorized_client_ids.includes(activeClient.id)
  );
  const canView = canViewReconciliationWorkspace(principal);
  const requestContext = useMemo(
    () => ({ devSubject, firmId }),
    [devSubject, firmId]
  );

  const refreshList = useCallback(async () => {
    if (!principal || !canView || !hasClientAccess) {
      setItems([]);
      setSelectedTransactionId(null);
      return;
    }
    setError(null);
    try {
      const nextItems =
        mode === "mock"
          ? mockReconciliationStore.listWorklist(
              activeClient.id,
              filter === "all" ? undefined : filter
            )
          : await listReconciliationWorklist(
              activeClient.id,
              requestContext,
              filter === "all" ? undefined : filter
            );
      setItems(nextItems);
      setSelectedTransactionId((current) => {
        if (current && nextItems.some((item) => item.transaction.id === current)) {
          return current;
        }
        return nextItems[0]?.transaction.id ?? null;
      });
    } catch (caught) {
      setItems([]);
      setSelectedTransactionId(null);
      setError(caught instanceof Error ? caught.message : "Unable to load reconciliation worklist.");
    }
  }, [activeClient.id, canView, filter, hasClientAccess, mode, principal, requestContext]);

  useEffect(() => {
    void refreshList();
  }, [refreshList]);

  const filteredItems = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return items;
    return items.filter((item) => {
      const transaction = item.transaction;
      return [
        transaction.reference,
        transaction.counterparty_name,
        transaction.description,
        transaction.source_transaction_id,
      ]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(query));
    });
  }, [items, search]);

  const selectedItem = useMemo(
    () => items.find((item) => item.transaction.id === selectedTransactionId) ?? null,
    [items, selectedTransactionId]
  );

  useEffect(() => {
    let cancelled = false;
    async function loadDetail() {
      setCandidates([]);
      setHistory(null);
      if (!selectedItem) return;
      try {
        if (selectedItem.latest_match_run) {
          const nextCandidates =
            mode === "mock"
              ? mockReconciliationStore.listCandidates(selectedItem.latest_match_run.id)
              : await listReconciliationCandidates(
                  activeClient.id,
                  selectedItem.transaction.id,
                  selectedItem.latest_match_run.id,
                  requestContext
                );
          if (!cancelled) setCandidates(nextCandidates);
        }
        if (selectedItem.review_id) {
          const nextHistory =
            mode === "mock"
              ? mockReconciliationStore.history(selectedItem.review_id)
              : await getReconciliationHistory(
                  activeClient.id,
                  selectedItem.transaction.id,
                  selectedItem.review_id,
                  requestContext
                );
          if (!cancelled) setHistory(nextHistory);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Unable to load reconciliation detail.");
        }
      }
    }
    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [activeClient.id, mode, requestContext, selectedItem]);

  const runMutation = useCallback(
    async (label: string, operation: () => Promise<unknown> | unknown) => {
      setBusy(label);
      setError(null);
      try {
        await operation();
        setNote("");
        await refreshList();
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : `${label} failed.`);
      } finally {
        setBusy(null);
      }
    },
    [refreshList]
  );

  if (mode === "live" && (connectionStatus !== "connected" || !effectivePrincipal)) {
    return (
      <div className="rounded-xl border border-amber-900/70 bg-amber-950/30 p-6 text-center">
        <AlertTriangle className="mx-auto mb-3 h-6 w-6 text-amber-400" />
        <h1 className="font-semibold text-slate-100">Bank Reconciliation Locked</h1>
        <p className="mt-2 text-xs text-slate-300">
          Live mode requires a verified backend context. No mock reconciliation authority is used as a fallback.
        </p>
      </div>
    );
  }

  if (!canView) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-center">
        <Lock className="mx-auto mb-3 h-6 w-6 text-slate-500" />
        <h1 className="font-semibold text-slate-100">Reconciliation Workspace Restricted</h1>
        <p className="mt-2 text-xs text-slate-400">
          {effectiveRole ?? "This principal"} does not hold the bank-reconciliation read permissions required for this workspace.
        </p>
      </div>
    );
  }

  if (!hasClientAccess) {
    return (
      <div className="rounded-xl border border-rose-900/70 bg-rose-950/30 p-6 text-center">
        <Shield className="mx-auto mb-3 h-6 w-6 text-rose-400" />
        <h1 className="font-semibold text-slate-100">Client Access Denied</h1>
        <p className="mt-2 text-xs text-slate-300">
          The active client is not present in the backend-authorized client set for this principal.
        </p>
      </div>
    );
  }

  const requireReason = () => {
    const reason = note.trim();
    if (!reason) {
      setError("A human-entered reason is required for this action.");
      return null;
    }
    return reason;
  };

  return (
    <div className="space-y-4">
      <section className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900 p-4">
        <div>
          <div className="flex items-center gap-2">
            <Banknote className="h-5 w-5 text-blue-400" />
            <h1 className="text-lg font-bold text-slate-100">Bank Reconciliation</h1>
            <span className="rounded border border-blue-900 bg-blue-950/60 px-2 py-0.5 font-mono text-[10px] text-blue-300">
              Phase 6
            </span>
          </div>
          <p className="mt-1 max-w-3xl text-xs text-slate-400">
            Deterministic matching proposes evidence only. A match score never approves a reconciliation; terminal outcomes require an authorized human action.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-[10px] text-slate-400">
            {mode === "mock" ? "Synthetic Mock" : "Live API"}
          </span>
          <button
            type="button"
            onClick={() => void refreshList()}
            disabled={busy !== null}
            className="inline-flex items-center gap-1 rounded border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
        </div>
      </section>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-rose-900 bg-rose-950/30 p-3 text-xs text-rose-200">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((entry) => (
              <button
                type="button"
                key={entry.value}
                onClick={() => setFilter(entry.value)}
                className={`rounded border px-2.5 py-1 text-[11px] font-medium transition ${
                  filter === entry.value
                    ? "border-blue-600 bg-blue-600 text-white"
                    : "border-slate-700 bg-slate-950 text-slate-400 hover:text-slate-200"
                }`}
              >
                {entry.label}
              </button>
            ))}
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-500" />
            <input
              aria-label="Search reconciliation worklist"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Reference, counterparty, source ID…"
              className="w-64 rounded border border-slate-700 bg-slate-950 py-1.5 pl-8 pr-3 text-xs text-slate-200 outline-none focus:border-blue-600"
            />
          </div>
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.08fr)_minmax(380px,0.92fr)]">
        <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-4 py-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
              Client Worklist · {activeClient.name}
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 font-mono text-[10px] uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2.5">Transaction</th>
                  <th className="px-3 py-2.5">Amount</th>
                  <th className="px-3 py-2.5">Workflow</th>
                  <th className="px-3 py-2.5">Activity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filteredItems.map((item) => {
                  const selected = item.transaction.id === selectedTransactionId;
                  return (
                    <tr
                      key={item.transaction.id}
                      onClick={() => setSelectedTransactionId(item.transaction.id)}
                      className={`cursor-pointer transition ${
                        selected ? "bg-blue-950/30" : "hover:bg-slate-800/40"
                      }`}
                    >
                      <td className="px-3 py-3">
                        <div className="font-medium text-slate-100">
                          {item.transaction.reference ?? item.transaction.source_transaction_id}
                        </div>
                        <div className="mt-0.5 text-[11px] text-slate-500">
                          {item.transaction.counterparty_name ?? item.transaction.description}
                        </div>
                      </td>
                      <td className="px-3 py-3 font-mono font-semibold text-slate-200">
                        {item.transaction.currency} {item.transaction.amount}
                      </td>
                      <td className="px-3 py-3">
                        <span className={`rounded border px-2 py-0.5 text-[10px] ${workflowClass(item.workflow_state)}`}>
                          {workflowLabel(item.workflow_state)}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-[10px] text-slate-500">
                        {displayDate(item.last_activity_at)}
                      </td>
                    </tr>
                  );
                })}
                {filteredItems.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-10 text-center text-xs text-slate-500">
                      No reconciliation transactions match this view.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="space-y-3">
          {!selectedItem ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-xs text-slate-500">
              Select a bank transaction to inspect deterministic evidence and human review history.
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-mono text-[10px] uppercase text-slate-500">Bank Transaction</div>
                    <h2 className="mt-1 font-semibold text-slate-100">
                      {selectedItem.transaction.reference ?? selectedItem.transaction.source_transaction_id}
                    </h2>
                    <p className="mt-1 text-xs text-slate-400">
                      {selectedItem.transaction.description}
                    </p>
                  </div>
                  <span className={`rounded border px-2 py-1 text-[10px] ${workflowClass(selectedItem.workflow_state)}`}>
                    {workflowLabel(selectedItem.workflow_state)}
                  </span>
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <dt className="text-[10px] uppercase text-slate-500">Amount</dt>
                    <dd className="mt-1 font-mono font-semibold text-slate-100">
                      {selectedItem.transaction.currency} {selectedItem.transaction.amount}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[10px] uppercase text-slate-500">Booking Date</dt>
                    <dd className="mt-1 text-slate-200">{selectedItem.transaction.booking_date}</dd>
                  </div>
                  <div>
                    <dt className="text-[10px] uppercase text-slate-500">Counterparty</dt>
                    <dd className="mt-1 text-slate-200">
                      {selectedItem.transaction.counterparty_name ?? "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[10px] uppercase text-slate-500">Source ID</dt>
                    <dd className="mt-1 font-mono text-[10px] text-slate-400">
                      {selectedItem.transaction.source_transaction_id}
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
                    Deterministic Match Evidence
                  </h3>
                  <span className="font-mono text-[10px] text-slate-500">
                    run {shortId(selectedItem.latest_match_run?.id)}
                  </span>
                </div>
                <div className="mt-2 flex items-start gap-2 rounded border border-amber-900/70 bg-amber-950/30 p-2.5 text-[11px] text-amber-200">
                  <Shield className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>
                    Candidate scores are deterministic evidence only. They cannot create or approve a reconciliation outcome.
                  </span>
                </div>
                <div className="mt-3 space-y-2">
                  {candidates.map((entry) => (
                    <div key={entry.id} className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-medium text-slate-100">
                            {entry.target_reference ?? shortId(entry.review_outcome_id)}
                          </div>
                          <div className="mt-0.5 text-[11px] text-slate-500">
                            {entry.target_counterparty_name ?? "No counterparty supplied"}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono text-sm font-bold text-blue-300">{entry.score}</div>
                          <div className="text-[9px] uppercase text-slate-600">evidence score</div>
                        </div>
                      </div>
                      <div className="mt-2 font-mono text-[10px] text-slate-400">
                        {entry.target_currency} {entry.target_amount} · {entry.target_transaction_date}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {entry.reasons.map((reason) => (
                          <span key={reason} className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[9px] text-slate-400">
                            {reason}
                          </span>
                        ))}
                      </div>
                      {canSelectReconciliationCandidate(principal, selectedItem) && (
                        <button
                          type="button"
                          disabled={busy !== null || selectedItem.selected_review_outcome_id === entry.review_outcome_id}
                          onClick={() =>
                            void runMutation("Select Candidate", () =>
                              mode === "mock"
                                ? mockReconciliationStore.selectCandidate(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.review_id!,
                                    entry.review_outcome_id
                                  )
                                : selectReconciliationCandidate(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.review_id!,
                                    entry.review_outcome_id,
                                    requestContext
                                  )
                            )
                          }
                          className="mt-2 rounded border border-blue-700 bg-blue-950/50 px-2 py-1 text-[10px] font-semibold text-blue-200 hover:bg-blue-900 disabled:opacity-50"
                        >
                          {selectedItem.selected_review_outcome_id === entry.review_outcome_id
                            ? "Selected"
                            : "Select Candidate"}
                        </button>
                      )}
                    </div>
                  ))}
                  {selectedItem.latest_match_run && candidates.length === 0 && (
                    <p className="rounded border border-slate-800 bg-slate-950 p-3 text-[11px] text-slate-500">
                      This deterministic match run produced no approved accounting candidate.
                    </p>
                  )}
                  {!selectedItem.latest_match_run && (
                    <p className="rounded border border-slate-800 bg-slate-950 p-3 text-[11px] text-slate-500">
                      No match run exists yet. An authorized reviewer may generate deterministic candidates.
                    </p>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
                  Human Reconciliation Controls
                </h3>
                {isReconciliationTerminal(selectedItem) ? (
                  <div className="mt-3 flex items-start gap-2 rounded border border-emerald-900/60 bg-emerald-950/20 p-3 text-xs text-emerald-200">
                    <Lock className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>
                      This reconciliation is terminal and read-only. History remains available; direct mutation controls are suppressed.
                    </span>
                  </div>
                ) : (
                  <>
                    <label className="mt-3 block text-[10px] uppercase text-slate-500" htmlFor="reconciliationNote">
                      Human note / required reason
                    </label>
                    <textarea
                      id="reconciliationNote"
                      value={note}
                      onChange={(event) => setNote(event.target.value)}
                      rows={2}
                      placeholder="Required for dispute, reopen, and unmatched decisions; optional for approval."
                      className="mt-1 w-full rounded border border-slate-700 bg-slate-950 p-2 text-xs text-slate-200 outline-none focus:border-blue-600"
                    />
                    <div className="mt-3 flex flex-wrap gap-2">
                      {canGenerateCandidates(principal, selectedItem) && (
                        <button
                          type="button"
                          disabled={busy !== null}
                          onClick={() =>
                            void runMutation("Generate Candidates", () =>
                              mode === "mock"
                                ? mockReconciliationStore.generateMatch(
                                    activeClient.id,
                                    selectedItem.transaction.id
                                  )
                                : generateReconciliationMatch(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    requestContext
                                  )
                            )
                          }
                          className="inline-flex items-center gap-1 rounded bg-blue-600 px-2.5 py-1.5 text-[11px] font-semibold text-white hover:bg-blue-500 disabled:opacity-50"
                        >
                          <Play className="h-3 w-3" /> Generate Candidates
                        </button>
                      )}
                      {canStartReconciliationReview(principal, selectedItem) && (
                        <button
                          type="button"
                          disabled={busy !== null}
                          onClick={() =>
                            void runMutation("Start Human Review", () =>
                              mode === "mock"
                                ? mockReconciliationStore.createReview(
                                    activeClient.id,
                                    selectedItem.transaction.id
                                  )
                                : createReconciliationReview(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.latest_match_run!.id,
                                    requestContext
                                  )
                            )
                          }
                          className="rounded border border-blue-700 bg-blue-950/40 px-2.5 py-1.5 text-[11px] font-semibold text-blue-200 hover:bg-blue-900 disabled:opacity-50"
                        >
                          Start Human Review
                        </button>
                      )}
                      {canDisputeReconciliation(principal, selectedItem) && (
                        <button
                          type="button"
                          disabled={busy !== null}
                          onClick={() => {
                            const reason = requireReason();
                            if (!reason) return;
                            void runMutation("Dispute", () =>
                              mode === "mock"
                                ? mockReconciliationStore.dispute(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.review_id!,
                                    reason
                                  )
                                : disputeReconciliationReview(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.review_id!,
                                    reason,
                                    requestContext
                                  )
                            );
                          }}
                          className="inline-flex items-center gap-1 rounded border border-rose-800 bg-rose-950/30 px-2.5 py-1.5 text-[11px] font-semibold text-rose-200 hover:bg-rose-900 disabled:opacity-50"
                        >
                          <XCircle className="h-3 w-3" /> Dispute
                        </button>
                      )}
                      {canReopenReconciliation(principal, selectedItem) && (
                        <button
                          type="button"
                          disabled={busy !== null}
                          onClick={() => {
                            const reason = requireReason();
                            if (!reason) return;
                            void runMutation("Reopen", () =>
                              mode === "mock"
                                ? mockReconciliationStore.reopen(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.review_id!,
                                    reason
                                  )
                                : reopenReconciliationReview(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.review_id!,
                                    reason,
                                    requestContext
                                  )
                            );
                          }}
                          className="inline-flex items-center gap-1 rounded border border-amber-800 bg-amber-950/30 px-2.5 py-1.5 text-[11px] font-semibold text-amber-200 hover:bg-amber-900 disabled:opacity-50"
                        >
                          <RotateCcw className="h-3 w-3" /> Reopen
                        </button>
                      )}
                      {canApproveReconciliation(principal, selectedItem) && (
                        <button
                          type="button"
                          disabled={busy !== null}
                          onClick={() =>
                            void runMutation("Approve Selected Match", () =>
                              mode === "mock"
                                ? mockReconciliationStore.approve(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.review_id!,
                                    note.trim() || null
                                  )
                                : approveReconciliationMatch(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.review_id!,
                                    note.trim() || null,
                                    requestContext
                                  )
                            )
                          }
                          className="inline-flex items-center gap-1 rounded bg-emerald-600 px-2.5 py-1.5 text-[11px] font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
                        >
                          <CheckCircle className="h-3 w-3" /> Approve Selected Match
                        </button>
                      )}
                      {canMarkReconciliationUnmatched(principal, selectedItem) && (
                        <button
                          type="button"
                          disabled={busy !== null}
                          onClick={() => {
                            const reason = requireReason();
                            if (!reason) return;
                            void runMutation("Mark Unmatched", () =>
                              mode === "mock"
                                ? mockReconciliationStore.markUnmatched(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.review_id!,
                                    reason
                                  )
                                : markReconciliationUnmatched(
                                    activeClient.id,
                                    selectedItem.transaction.id,
                                    selectedItem.review_id!,
                                    reason,
                                    requestContext
                                  )
                            );
                          }}
                          className="rounded border border-slate-600 bg-slate-800 px-2.5 py-1.5 text-[11px] font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                        >
                          Mark Unmatched
                        </button>
                      )}
                    </div>
                    {busy && <p className="mt-2 text-[10px] text-blue-300">{busy} in progress…</p>}
                  </>
                )}
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex items-center gap-2">
                  <History className="h-4 w-4 text-slate-400" />
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-300">
                    Immutable Review History
                  </h3>
                </div>
                {!history ? (
                  <p className="mt-3 text-[11px] text-slate-500">
                    No human reconciliation review has been created for this transaction.
                  </p>
                ) : (
                  <div className="mt-3 space-y-2">
                    <div className="rounded border border-slate-800 bg-slate-950 p-2 text-[10px] text-slate-400">
                      Review {shortId(history.review.id)} · status {history.review.status} · match run {shortId(history.review.match_run_id)}
                    </div>
                    {history.actions.map((entry) => (
                      <div key={entry.id} className="border-l-2 border-slate-700 pl-3 text-[11px]">
                        <div className="font-medium text-slate-200">{entry.action_type}</div>
                        <div className="text-[10px] text-slate-500">{displayDate(entry.created_at)}</div>
                        {entry.reason && <p className="mt-1 text-slate-400">{entry.reason}</p>}
                      </div>
                    ))}
                    {history.outcome && (
                      <div className="rounded border border-emerald-900/60 bg-emerald-950/20 p-3 text-[11px] text-emerald-200">
                        Terminal outcome: <strong>{history.outcome.outcome_type}</strong>
                        {history.outcome.reason ? ` — ${history.outcome.reason}` : ""}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
