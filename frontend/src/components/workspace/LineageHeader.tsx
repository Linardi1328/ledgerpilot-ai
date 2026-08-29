import React from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ReviewTaskLineage } from "@/types/api";

export function LineageHeader({
  lineage,
  submittedFilename,
  sha256,
}: {
  lineage: ReviewTaskLineage;
  submittedFilename?: string;
  sha256?: string | null;
}) {
  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
      <div className="flex items-center space-x-3">
        <Link
          href="/reviews"
          className="text-slate-400 hover:text-slate-200 transition font-medium flex items-center space-x-1"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Queue</span>
        </Link>

        <div className="h-4 w-px bg-slate-800" />

        <div className="font-mono text-slate-300">
          <span className="text-slate-500">Doc:</span>{" "}
          <span className="text-slate-200 font-semibold">{submittedFilename || lineage.documentId}</span>
        </div>

        <div className="font-mono text-slate-400 text-[11px] hidden sm:block">
          <span className="text-slate-500">Task:</span>{" "}
          <span className="text-slate-300">{lineage.reviewTaskId.slice(0, 8)}...</span>
        </div>

        {sha256 && (
          <div className="font-mono text-slate-500 text-[11px] hidden md:block">
            SHA: <span className="text-slate-400">{sha256.slice(0, 12)}...</span>
          </div>
        )}
      </div>

      <div className="text-[11px] font-mono text-slate-400 flex items-center space-x-2">
        <span className="text-slate-500">Decision Run:</span>
        <span className="text-slate-300">{lineage.decisionRunId.slice(0, 8)}</span>
      </div>
    </div>
  );
}
