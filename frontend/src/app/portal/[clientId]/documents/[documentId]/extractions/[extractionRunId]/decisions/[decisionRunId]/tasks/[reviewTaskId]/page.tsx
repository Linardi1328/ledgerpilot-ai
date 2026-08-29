"use client";

import React, { useEffect, useState, useCallback, use } from "react";
import { useAuth } from "@/lib/context/AuthContext";
import { Permission, Role } from "@/types/roles";
import {
  DocumentMetadataResponse,
  ReviewCommentResponse,
  ReviewTaskLineage,
} from "@/types/api";
import { mockDataStore } from "@/lib/mock/mock-client";
import { defaultApiClient } from "@/lib/api/client";
import {
  getOutstandingInformationRequest,
  respondToInformationRequest,
} from "@/lib/api/reviews";
import { fetchDocumentMetadata } from "@/lib/api/documents";
import { PortalCard, PortalSuccess } from "@/components/client-portal/PortalCard";
import { useRouter } from "next/navigation";
import { AlertCircle } from "lucide-react";

interface PortalParams {
  clientId: string;
  documentId: string;
  extractionRunId: string;
  decisionRunId: string;
  reviewTaskId: string;
}

export default function ClientSubmitterPortalPage({
  params: paramsPromise,
}: {
  params: Promise<PortalParams>;
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

  const [documentMeta, setDocumentMeta] = useState<DocumentMetadataResponse | null>(null);
  const [inquiry, setInquiry] = useState<ReviewCommentResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  // Authoritative Role and Permission guards
  const isClientSubmitter = effectiveRole === Role.CLIENT_SUBMITTER;
  const canViewInquiry =
    isClientSubmitter &&
    (effectivePrincipal?.permissions.includes(Permission.VIEW_INFORMATION_REQUEST) ?? false);
  const canRespondInquiry =
    canViewInquiry &&
    (effectivePrincipal?.permissions.includes(Permission.RESPOND_TO_INFORMATION_REQUEST) ?? false);

  const loadPortalData = useCallback(async () => {
    // If not authorized to view information requests, fail closed immediately without fetching
    if (!canViewInquiry) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    if (mode === "mock") {
      try {
        const doc = mockDataStore.getDocument(lineage.clientId, lineage.documentId);
        setDocumentMeta(doc);
        const outstanding = mockDataStore.getOutstandingInfoRequest(lineage);
        setInquiry(outstanding);
      } catch {
        setInquiry(null);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    try {
      const [doc, outstandingInquiry] = await Promise.all([
        fetchDocumentMetadata(lineage.clientId, lineage.documentId, defaultApiClient, {
          devSubject,
          firmId,
        }),
        getOutstandingInformationRequest(lineage, defaultApiClient, {
          devSubject,
          firmId,
        }),
      ]);

      setDocumentMeta(doc);
      setInquiry(outstandingInquiry);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load inquiry.");
    } finally {
      setIsLoading(false);
    }
  }, [mode, canViewInquiry, lineage, devSubject, firmId]);

  useEffect(() => {
    loadPortalData();
  }, [loadPortalData]);

  const handleResponseSubmit = async (responseBody: string) => {
    if (!canRespondInquiry) {
      setError("You do not hold permission to respond to information requests.");
      return;
    }

    if (mode === "mock") {
      mockDataStore.respondToInfo(lineage, responseBody);
      setIsSuccess(true);
      return;
    }

    await respondToInformationRequest(lineage, responseBody, defaultApiClient, {
      devSubject,
      firmId,
    });
    setIsSuccess(true);
  };

  // Route-Level Authority Guards
  if (mode === "live" && (effectiveRole === null || connectionStatus !== "connected")) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-4 max-w-xl mx-auto shadow-2xl">
        <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-amber-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="font-bold text-base text-slate-100">Portal Access Locked</h2>
        <p className="text-xs text-slate-300 leading-relaxed">
          {connectionStatus === "unauthenticated"
            ? "Authentication required to access client portal inquiries."
            : connectionStatus === "invalid_context"
            ? "Authoritative context payload failed validation. Access locked."
            : "The FastAPI backend server is unreachable. Live mode failed closed."}
        </p>
      </div>
    );
  }

  if (!isClientSubmitter) {
    return (
      <div className="bg-slate-900 border border-purple-900/60 rounded-xl p-8 text-center space-y-4 max-w-xl mx-auto shadow-2xl">
        <div className="w-12 h-12 rounded-full bg-purple-950 border border-purple-800 flex items-center justify-center mx-auto text-purple-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="font-bold text-base text-slate-100">Restricted Submitter Access</h2>
        <p className="text-xs text-slate-300 leading-relaxed">
          Your current verified role is not authorized to access the Client Information Portal. This route requires an authenticated <strong>Client Submitter</strong> principal.
        </p>
      </div>
    );
  }

  if (!canViewInquiry) {
    return (
      <div className="bg-slate-900 border border-purple-900/60 rounded-xl p-8 text-center space-y-4 max-w-xl mx-auto shadow-2xl">
        <div className="w-12 h-12 rounded-full bg-purple-950 border border-purple-800 flex items-center justify-center mx-auto text-purple-400">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="font-bold text-base text-slate-100">Permission Required</h2>
        <p className="text-xs text-slate-300 leading-relaxed">
          Your account holds the Client Submitter role but lacks the required <code>VIEW_INFORMATION_REQUEST</code> permission to inspect inquiry content.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px] text-xs text-slate-400 font-mono">
        <span className="w-4 h-4 mr-2 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
        <span>Loading Client Information Request...</span>
      </div>
    );
  }

  if (isSuccess) {
    return <PortalSuccess onReset={() => router.push("/portal")} />;
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="max-w-2xl mx-auto bg-amber-950/40 border border-amber-800 text-amber-200 p-3 rounded-lg text-xs">
          Notice: {error}
        </div>
      )}

      <PortalCard
        documentFilename={documentMeta?.submitted_filename}
        inquiry={inquiry}
        canRespond={canRespondInquiry}
        onSubmitResponse={handleResponseSubmit}
      />
    </div>
  );
}
