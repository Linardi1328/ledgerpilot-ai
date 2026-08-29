"use client";

import React, { useState } from "react";
import { useAuth } from "@/lib/context/AuthContext";
import { useClientContext } from "@/lib/context/ClientContext";
import { UploadCloud, CheckCircle, ArrowRight, Play, AlertCircle } from "lucide-react";
import { uploadDocument } from "@/lib/api/documents";
import { createExtractionRun } from "@/lib/api/extractions";
import { createAccountingDecisionRun } from "@/lib/api/accounting";
import { createReviewTask } from "@/lib/api/reviews";
import { defaultApiClient } from "@/lib/api/client";
import { buildLiveReviewTaskUrl } from "@/lib/api/lineage";
import Link from "next/link";

export default function IntakePipelinePage() {
  const { mode, devSubject, firmId, principal } = useAuth();
  const { activeClient } = useClientContext();

  const [file, setFile] = useState<File | null>(null);
  const [pipelineStep, setPipelineStep] = useState<string | null>(null);
  const [createdUrl, setCreatedUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleRunPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please choose a synthetic PDF or image file.");
      return;
    }

    try {
      setIsProcessing(true);
      setError(null);
      setCreatedUrl(null);

      if (mode === "mock") {
        setPipelineStep("1/4: Uploading synthetic document...");
        await new Promise((r) => setTimeout(r, 400));
        setPipelineStep("2/4: Running extraction provider...");
        await new Promise((r) => setTimeout(r, 400));
        setPipelineStep("3/4: Evaluating accounting decision & rules...");
        await new Promise((r) => setTimeout(r, 400));
        setPipelineStep("4/4: Initializing human review task...");
        await new Promise((r) => setTimeout(r, 400));

        setCreatedUrl(
          `/reviews/${activeClient.id}/documents/d0000001-0000-0000-0000-000000000001/extractions/e0000001-0000-0000-0000-000000000001/decisions/a0000001-0000-0000-0000-000000000001/tasks/r0000001-0000-0000-0000-000000000001`
        );
        setPipelineStep("Pipeline Succeeded! Review Task Ready.");
        return;
      }

      // Live Mode: Execute sequential live backend steps
      setPipelineStep("1/4: Uploading document to FastAPI...");
      const doc = await uploadDocument(activeClient.id, file, defaultApiClient, {
        devSubject,
        firmId,
      });

      setPipelineStep("2/4: Executing extraction run...");
      const ext = await createExtractionRun(activeClient.id, doc.id, defaultApiClient, {
        devSubject,
        firmId,
      });

      setPipelineStep("3/4: Evaluating deterministic decision engine...");
      const dec = await createAccountingDecisionRun(
        activeClient.id,
        doc.id,
        ext.id,
        defaultApiClient,
        { devSubject, firmId }
      );

      setPipelineStep("4/4: Creating Phase 5 review task...");
      const task = await createReviewTask(
        {
          clientId: activeClient.id,
          documentId: doc.id,
          extractionRunId: ext.id,
          decisionRunId: dec.id,
        },
        principal?.membership_id,
        defaultApiClient,
        { devSubject, firmId }
      );

      const liveUrl = buildLiveReviewTaskUrl({
        clientId: activeClient.id,
        documentId: doc.id,
        extractionRunId: ext.id,
        decisionRunId: dec.id,
        reviewTaskId: task.id,
      });

      setCreatedUrl(liveUrl);
      setPipelineStep("Live Pipeline Succeeded! Review Task Ready.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Pipeline execution failed.");
      setPipelineStep(null);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-3 shadow-xl">
        <div className="flex items-center space-x-2 text-blue-400 font-bold text-base">
          <UploadCloud className="w-5 h-5" />
          <span>Document Intake Pipeline</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          Upload synthetic invoices or receipts to move sequentially through:
          <strong className="text-slate-100 block mt-1">
            Document Upload → Field Extraction → Deterministic Accounting Decision → Human Review Task
          </strong>
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 shadow-xl">
        <form onSubmit={handleRunPipeline} className="space-y-4 text-xs">
          <div>
            <label htmlFor="fileInput" className="block font-semibold text-slate-200 mb-1">
              Select Synthetic Invoice (PDF, PNG, JPG):
            </label>
            <input
              id="fileInput"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-300 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-500 cursor-pointer"
            />
            <p className="text-[10px] text-slate-500 mt-1">
              * Non-negotiable repository rule: Never upload real financial, personal, or client documents. Use synthetic files only.
            </p>
          </div>

          {error && (
            <div className="bg-rose-950/60 border border-rose-800 text-rose-300 p-3 rounded flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {pipelineStep && (
            <div className="bg-slate-950 p-3 rounded border border-slate-800 font-mono text-xs text-blue-400">
              {pipelineStep}
            </div>
          )}

          {createdUrl && (
            <div className="bg-emerald-950/40 border border-emerald-800 p-4 rounded-lg space-y-2 text-emerald-200">
              <div className="flex items-center space-x-2 font-bold text-emerald-300">
                <CheckCircle className="w-4 h-4" />
                <span>Review Task Generated Successfully</span>
              </div>
              <p className="text-[11px] text-slate-300">
                The document has moved through extraction and deterministic evaluation. Click below to launch the Review Workspace:
              </p>
              <div className="pt-1">
                <Link
                  href={createdUrl}
                  className="inline-flex items-center space-x-1.5 px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition shadow"
                >
                  <span>Open Review Workspace</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={isProcessing || !file}
              className="px-5 py-2 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition flex items-center space-x-1.5 disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{isProcessing ? "Processing Pipeline..." : "Execute Intake Pipeline"}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
