"use client";

import React, { useEffect, useState, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/context/AuthContext";
import { Role } from "@/types/roles";
import {
  AccountingDecisionRunResponse,
  DocumentMetadataResponse,
  ExtractedFieldResponse,
  ExtractionFieldCorrectionRequest,
  ExtractionRunResponse,
  ReviewHistoryResponse,
  ReviewTaskLineage,
  ReviewTaskResponse,
} from "@/types/api";
import { mockDataStore } from "@/lib/mock/mock-client";
import { defaultApiClient } from "@/lib/api/client";
import {
  addReviewComment,
  approveReviewTask,
  createReviewTask,
  escalateReviewTask,
  fetchReviewHistory,
  fetchReviewTask,
  rejectReviewTask,
  requestInformation,
} from "@/lib/api/reviews";
import { createAccountingDecisionRun, fetchAccountingDecisionRun } from "@/lib/api/accounting";
import { addFieldCorrection, fetchExtractionRun } from "@/lib/api/extractions";
import { fetchDocumentMetadata } from "@/lib/api/documents";
import { buildLiveReviewTaskUrl } from "@/lib/api/lineage";
import {
  canComment,
  canCorrectField,
  canRegenerateAccountingDecision,
  isTerminalTask,
} from "@/lib/policy/action-policy";
import { LineageHeader } from "@/components/workspace/LineageHeader";
import { RiskStatusBanner } from "@/components/workspace/RiskStatusBanner";
import { JournalTable } from "@/components/workspace/JournalTable";
import { FindingsList } from "@/components/workspace/FindingsList";
import { SupplierMatchCard } from "@/components/workspace/SupplierMatchCard";
import { DuplicateCard } from "@/components/workspace/DuplicateCard";
import { RecommendationsCard } from "@/components/workspace/RecommendationsCard";
import { EvidenceTable } from "@/components/workspace/EvidenceTable";
import { CommentsFeed } from "@/components/workspace/CommentsFeed";
import { AuditTimeline } from "@/components/workspace/AuditTimeline";
import { ActionBar } from "@/components/workspace/ActionBar";
import { TerminalBanner } from "@/components/workspace/TerminalBanner";
import { ApproveDialog } from "@/components/dialogs/ApproveDialog";
import { EscalateDialog } from "@/components/dialogs/EscalateDialog";
import { InfoRequestDialog } from "@/components/dialogs/InfoRequestDialog";
import { RejectDialog } from "@/components/dialogs/RejectDialog";
import { CorrectionDialog } from "@/components/dialogs/CorrectionDialog";
import { StaleDecisionDialog } from "@/components/dialogs/StaleDecisionDialog";
import { AlertCircle, Eye } from "lucide-react";
import { ApiError } from "@/lib/api/errors";

interface WorkspaceParams {
  clientId: string;
  documentId: string;
  extractionRunId: string;
  decisionRunId: string;
  reviewTaskId: string;
}

export default function ReviewWorkspacePage({
  params: paramsPromise,
}: {
  params: Promise<WorkspaceParams>;
}) {
  const params = use(paramsPromise);
  const router = useRouter();
  const { mode, effectiveRole, effectivePrincipal, devSubject, firmId, connectionStatus } = useAuth();

  const lineage: ReviewTaskLineage = React.useMemo(() => ({
    clientId: params.clientId,
    documentId: params.documentId,
    extractionRunId: params.extractionRunId,
    decisionRunId: params.decisionRunId,
    reviewTaskId: params.reviewTaskId,
  }), [params.clientId, params.documentId, params.extractionRunId, params.decisionRunId, params.reviewTaskId]);

  // State
  const [task, setTask] = useState<ReviewTaskResponse | null>(null);
  const [decision, setDecision] = useState<AccountingDecisionRunResponse | null>(null);
  const [extraction, setExtraction] = useState<ExtractionRunResponse | null>(null);
  const [documentMeta, setDocumentMeta] = useState<DocumentMetadataResponse | null>(null);
  const [history, setHistory] = useState<ReviewHistoryResponse | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isStale, setIsStale] = useState(false);

  // Dialog states
  const [showApproveDialog, setShowApproveDialog] = useState(false);
  const [showEscalateDialog, setShowEscalateDialog] = useState(false);
  const [showInfoRequestDialog, setShowInfoRequestDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [selectedCorrectionField, setSelectedCorrectionField] = useState<ExtractedFieldResponse | null>(null);
  const [showStaleDialog, setShowStaleDialog] = useState(false);

  // Load Data
  const loadData = useCallback(async () => {
    // If not authorized to view review workspace, skip fetch
    if (
      effectiveRole === Role.CLIENT_SUBMITTER ||
      effectiveRole === Role.FIRM_ADMIN ||
      (mode === "live" && effectiveRole === null)
    ) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setFetchError(null);

    if (mode === "mock") {
      try {
        const scenario = mockDataStore.getScenario(lineage.reviewTaskId);
        setTask(scenario.task);
        setDecision(scenario.decision);
        setExtraction(scenario.extraction);
        setDocumentMeta(scenario.document);
        setHistory(scenario.history);
      } catch (err: unknown) {
        setFetchError(err instanceof Error ? err.message : "Scenario not found in mock store.");
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // Live Mode: Fetch from backend endpoints
    try {
      const [fetchedTask, fetchedDecision, fetchedExtraction, fetchedDoc, fetchedHist] =
        await Promise.all([
          fetchReviewTask(lineage, defaultApiClient, { devSubject, firmId }),
          fetchAccountingDecisionRun(
            lineage.clientId,
            lineage.documentId,
            lineage.extractionRunId,
            lineage.decisionRunId,
            defaultApiClient,
            { devSubject, firmId }
          ),
          fetchExtractionRun(
            lineage.clientId,
            lineage.documentId,
            lineage.extractionRunId,
            defaultApiClient,
            { devSubject, firmId }
          ),
          fetchDocumentMetadata(lineage.clientId, lineage.documentId, defaultApiClient, {
            devSubject,
            firmId,
          }),
          fetchReviewHistory(lineage, defaultApiClient, { devSubject, firmId }),
        ]);

      setTask(fetchedTask);
      setDecision(fetchedDecision);
      setExtraction(fetchedExtraction);
      setDocumentMeta(fetchedDoc);
      setHistory(fetchedHist);
      // Corrected fields alone do NOT make the decision stale on initial load.
    } catch (err: unknown) {
      setFetchError(err instanceof Error ? err.message : "Failed to load live review workspace.");
    } finally {
      setIsLoading(false);
    }
  }, [mode, effectiveRole, lineage, devSubject, firmId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Mutation Handlers
  const handleApprove = async (note?: string) => {
    try {
      if (mode === "mock") {
        const res = mockDataStore.approve(lineage, note, effectivePrincipal || undefined);
        setTask({ ...res.task });
        setHistory({ ...mockDataStore.getHistory(lineage) });
        return;
      }

      const res = await approveReviewTask(lineage, note, defaultApiClient, { devSubject, firmId });
      setTask({ ...res.task });
      await loadData();
    } catch (err: unknown) {
      if (err instanceof ApiError && err.code === "decision_stale_after_correction") {
        setIsStale(true);
        setShowStaleDialog(true);
      }
      throw err;
    }
  };

  const handleEscalate = async (seniorMembershipId: string, reason: string) => {
    if (mode === "mock") {
      const updatedTask = mockDataStore.escalate(lineage, seniorMembershipId, reason, effectivePrincipal || undefined);
      setTask({ ...updatedTask });
      setHistory({ ...mockDataStore.getHistory(lineage) });
      return;
    }

    const updatedTask = await escalateReviewTask(
      lineage,
      seniorMembershipId,
      reason,
      defaultApiClient,
      { devSubject, firmId }
    );
    setTask({ ...updatedTask });
    await loadData();
  };

  const handleRequestInfo = async (question: string) => {
    if (mode === "mock") {
      const res = mockDataStore.requestInfo(lineage, question, effectivePrincipal || undefined);
      setTask({ ...res.task });
      setHistory({ ...mockDataStore.getHistory(lineage) });
      return;
    }

    const res = await requestInformation(lineage, question, defaultApiClient, {
      devSubject,
      firmId,
    });
    setTask({ ...res.task });
    await loadData();
  };

  const handleReject = async (reason: string) => {
    if (mode === "mock") {
      const res = mockDataStore.reject(lineage, reason, effectivePrincipal || undefined);
      setTask({ ...res.task });
      setHistory({ ...mockDataStore.getHistory(lineage) });
      return;
    }

    const res = await rejectReviewTask(lineage, reason, defaultApiClient, { devSubject, firmId });
    setTask({ ...res.task });
    await loadData();
  };

  const handleAddComment = async (body: string) => {
    if (mode === "mock") {
      mockDataStore.addComment(lineage, body, effectivePrincipal || undefined);
      setHistory({ ...mockDataStore.getHistory(lineage) });
      return;
    }

    await addReviewComment(lineage, body, defaultApiClient, { devSubject, firmId });
    await loadData();
  };

  const handleConfirmCorrection = async (
    fieldId: string,
    req: ExtractionFieldCorrectionRequest
  ) => {
    if (mode === "mock") {
      mockDataStore.addCorrection(lineage, fieldId, req);
      setExtraction({ ...mockDataStore.getExtraction(lineage) });
      // Correction performed in current session makes current decision stale
      setIsStale(true);
      return;
    }

    await addFieldCorrection(
      lineage.clientId,
      lineage.documentId,
      lineage.extractionRunId,
      fieldId,
      req,
      defaultApiClient,
      { devSubject, firmId }
    );
    // Correction performed in current session makes current decision stale
    setIsStale(true);
    await loadData();
  };

  const handleGenerateFreshDecision = async (
    setStep: (step: string) => void,
    existingDecisionId?: string | null
  ) => {
    if (mode === "mock") {
      setStep("1/3: Evaluating fresh deterministic decision...");
      await new Promise((r) => setTimeout(r, 200));
      setStep("2/3: Initializing new review task...");
      const res = mockDataStore.generateFreshDecisionAndTask(lineage, effectivePrincipal || undefined);
      setStep("3/3: Redirecting to fresh review task...");
      await new Promise((r) => setTimeout(r, 200));
      router.push(buildLiveReviewTaskUrl(res.newLineage));
      return;
    }

    let decisionRunId = existingDecisionId;

    if (!decisionRunId) {
      setStep("1/3: Generating fresh accounting decision run from corrected source...");
      const freshDecision = await createAccountingDecisionRun(
        lineage.clientId,
        lineage.documentId,
        lineage.extractionRunId,
        defaultApiClient,
        { devSubject, firmId }
      );
      decisionRunId = freshDecision.id;
    }

    setStep("2/3: Creating new review task for fresh decision...");
    try {
      const freshTask = await createReviewTask(
        {
          clientId: lineage.clientId,
          documentId: lineage.documentId,
          extractionRunId: lineage.extractionRunId,
          decisionRunId,
        },
        effectivePrincipal?.membership_id,
        defaultApiClient,
        { devSubject, firmId }
      );

      setStep("3/3: Redirecting to new review task...");
      const freshUrl = buildLiveReviewTaskUrl({
        clientId: lineage.clientId,
        documentId: lineage.documentId,
        extractionRunId: lineage.extractionRunId,
        decisionRunId,
        reviewTaskId: freshTask.id,
      });

      router.push(freshUrl);
    } catch (taskErr: unknown) {
      const enhancedError = new Error(
        taskErr instanceof Error
          ? taskErr.message
          : "Review task creation failed after decision was generated."
      );
      (enhancedError as unknown as { createdDecisionId: string }).createdDecisionId = decisionRunId;
      throw enhancedError;
    }
  };

  // Role Access Isolation Guards
  if (mode === "live" && (effectiveRole === null || connectionStatus !== "connected")) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-4 max-w-xl mx-auto shadow-2xl">
        <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-amber-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="font-bold text-base text-slate-100">Review Workspace Locked</h2>
        <p className="text-xs text-slate-300 leading-relaxed">
          {connectionStatus === "unauthenticated"
            ? "Authentication required to access review tasks."
            : "The FastAPI backend server is unreachable. Live mode has failed closed to protect accounting integrity."}
        </p>
      </div>
    );
  }

  if (effectiveRole === Role.CLIENT_SUBMITTER) {
    return (
      <div className="bg-slate-900 border border-purple-900/60 rounded-xl p-8 text-center space-y-4 max-w-xl mx-auto shadow-2xl">
        <div className="w-12 h-12 rounded-full bg-purple-950 border border-purple-800 flex items-center justify-center mx-auto text-purple-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="font-bold text-base text-slate-100">Restricted Access</h2>
        <p className="text-xs text-slate-300 leading-relaxed">
          Client Submitters are not authorized to view internal accounting review workspaces, proposed double-entry journals, recommendations, or reviewer comments.
        </p>
      </div>
    );
  }

  if (effectiveRole === Role.FIRM_ADMIN) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-4 max-w-xl mx-auto shadow-2xl">
        <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-slate-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="font-bold text-base text-slate-100">Review Workspace Unavailable to Firm Admin</h2>
        <p className="text-xs text-slate-300 leading-relaxed">
          Under the Phase 5 RBAC model, Firm Administrators do not hold review or accounting authorization permissions. To review this task, switch to an <strong>Accountant</strong> or <strong>Senior Reviewer</strong> principal.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px] text-xs text-slate-400 font-mono">
        <span className="w-4 h-4 mr-2 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <span>Loading Review Task Workspace...</span>
      </div>
    );
  }

  if (fetchError || !task) {
    return (
      <div className="bg-slate-900 border border-rose-900/80 rounded-xl p-6 text-center space-y-3 max-w-xl mx-auto">
        <div className="text-rose-400 font-bold text-sm">Failed to Load Review Task</div>
        <p className="text-xs text-slate-300 font-mono">{fetchError || "Task record not found."}</p>
        <button
          onClick={loadData}
          className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  const isAuditor = effectiveRole === Role.AUDITOR;
  const isTerminal = isTerminalTask(task);
  const allowCorrection = canCorrectField(effectivePrincipal, task);
  const allowRegenerate = canRegenerateAccountingDecision(effectivePrincipal);
  const allowComment = canComment(effectivePrincipal, task);

  return (
    <div className="space-y-4 text-slate-100">
      {/* Read-Only Banner for Auditor */}
      {isAuditor && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 text-xs text-slate-200 flex items-center space-x-2">
          <Eye className="w-4 h-4 text-slate-400 shrink-0" />
          <span>
            <strong>Auditor Read-Only Mode</strong>: You are viewing this review task with audit inspection permissions. All mutation controls and approval actions are suppressed.
          </span>
        </div>
      )}

      {/* Stale Decision Notice Banner */}
      {isStale && !isTerminal && (
        <div className="bg-amber-950/60 border border-amber-800 rounded-lg p-3 text-xs text-amber-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Accounting decision is out of date</strong>: Source information changed after this accounting decision was generated.
              {!allowRegenerate && (
                <span className="ml-1 text-amber-300">
                  An authorized reviewer must generate a fresh decision.
                </span>
              )}
            </span>
          </div>
          {allowRegenerate && (
            <button
              onClick={() => setShowStaleDialog(true)}
              className="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white font-semibold text-[11px] transition shrink-0 ml-2"
            >
              Resolve Stale Decision
            </button>
          )}
        </div>
      )}

      {/* Lineage Header */}
      <LineageHeader
        lineage={lineage}
        submittedFilename={documentMeta?.submitted_filename}
        sha256={documentMeta?.sha256}
      />

      {/* Risk and Status Banner */}
      <RiskStatusBanner task={task} />

      {/* Main High-Density Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left Column (2 Cols): Proposed Journal, Findings, Recommendations, Evidence */}
        <div className="lg:col-span-2 space-y-4">
          {/* Proposed Double-Entry Journal */}
          <JournalTable journal={decision?.proposed_journal} />

          {/* Deterministic Findings */}
          <FindingsList findings={decision?.findings || []} />

          {/* Supplier Match */}
          <SupplierMatchCard match={decision?.supplier_match} />

          {/* Duplicate Candidates */}
          <DuplicateCard candidates={decision?.duplicate_candidates || []} />

          {/* Accounting Recommendations */}
          <RecommendationsCard recommendations={decision?.recommendations || []} />

          {/* Extracted Source Evidence Table */}
          <EvidenceTable
            fields={extraction?.fields || []}
            canCorrect={allowCorrection && !isTerminal}
            onOpenCorrection={(field) => setSelectedCorrectionField(field)}
          />
        </div>

        {/* Right Column (1 Col): Comments & Audit Log */}
        <div className="space-y-4">
          {/* Reviewer Comments Feed */}
          <CommentsFeed
            comments={history?.comments || []}
            canAddComment={allowComment}
            onAddComment={handleAddComment}
          />

          {/* Audit Event Timeline */}
          <AuditTimeline events={history?.audit_events || []} />
        </div>
      </div>

      {/* Bottom Sticky Action Bar or Terminal Certificate */}
      <div className="pt-2">
        {isTerminal ? (
          <TerminalBanner task={task} outcome={history?.outcome} />
        ) : !isAuditor ? (
          <ActionBar
            task={task}
            journal={decision?.proposed_journal}
            principal={effectivePrincipal}
            isStale={isStale}
            onOpenApprove={() => setShowApproveDialog(true)}
            onOpenEscalate={() => setShowEscalateDialog(true)}
            onOpenInfoRequest={() => setShowInfoRequestDialog(true)}
            onOpenReject={() => setShowRejectDialog(true)}
          />
        ) : null}
      </div>

      {/* Dialog Modals */}
      <ApproveDialog
        isOpen={showApproveDialog}
        onClose={() => setShowApproveDialog(false)}
        task={task}
        journal={decision?.proposed_journal || null}
        principal={effectivePrincipal}
        onConfirmApprove={handleApprove}
      />

      <EscalateDialog
        isOpen={showEscalateDialog}
        onClose={() => setShowEscalateDialog(false)}
        onConfirmEscalate={handleEscalate}
      />

      <InfoRequestDialog
        isOpen={showInfoRequestDialog}
        onClose={() => setShowInfoRequestDialog(false)}
        onConfirmRequest={handleRequestInfo}
      />

      <RejectDialog
        isOpen={showRejectDialog}
        onClose={() => setShowRejectDialog(false)}
        onConfirmReject={handleReject}
      />

      <CorrectionDialog
        isOpen={selectedCorrectionField !== null}
        onClose={() => setSelectedCorrectionField(null)}
        field={selectedCorrectionField}
        onConfirmCorrection={handleConfirmCorrection}
      />

      <StaleDecisionDialog
        isOpen={showStaleDialog}
        onClose={() => setShowStaleDialog(false)}
        onGenerateFreshDecision={handleGenerateFreshDecision}
      />
    </div>
  );
}
