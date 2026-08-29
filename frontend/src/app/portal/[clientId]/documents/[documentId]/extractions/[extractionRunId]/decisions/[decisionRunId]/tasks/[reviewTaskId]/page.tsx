"use client";

import React, { useEffect, useState, useCallback, use } from "react";
import { useAuth } from "@/lib/context/AuthContext";
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
  const { mode, devSubject, firmId } = useAuth();

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

  const loadPortalData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    if (mode === "mock") {
      try {
        const doc = mockDataStore.getDocument(lineage.clientId, lineage.documentId);
        setDocumentMeta(doc);
        const outstanding = mockDataStore.getOutstandingInfoRequest(lineage);
        setInquiry(outstanding);
      } catch {
        // May not have an outstanding request yet; provide fallback or null
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
  }, [mode, lineage, devSubject, firmId]);

  useEffect(() => {
    loadPortalData();
  }, [loadPortalData]);

  const handleResponseSubmit = async (responseBody: string) => {
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
        onSubmitResponse={handleResponseSubmit}
      />
    </div>
  );
}
