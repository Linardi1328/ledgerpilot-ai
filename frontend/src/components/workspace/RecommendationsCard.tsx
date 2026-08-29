import React from "react";
import { AccountingRecommendationResponse } from "@/types/api";
import { Lightbulb } from "lucide-react";

export function RecommendationsCard({
  recommendations,
}: {
  recommendations: AccountingRecommendationResponse[];
}) {
  const getRecommendationTitle = (type: string) => {
    switch (type) {
      case "gl_account":
        return "Recommended GL Account";
      case "tax_code":
        return "Recommended Tax Code";
      case "cost_centre":
        return "Recommended Cost Centre";
      case "category":
        return "Recommended Category";
      default:
        return `Recommended ${type}`;
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3 text-slate-100">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <span className="font-semibold text-xs text-slate-200 flex items-center space-x-1.5">
          <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
          <span>Accounting Coding Recommendations</span>
        </span>
        <span className="text-[10px] font-mono text-slate-400">Recommendations Only</span>
      </div>

      {recommendations.length === 0 ? (
        <div className="text-xs text-slate-400 p-3 text-center bg-slate-950/60 rounded border border-slate-800">
          No coding recommendations generated.
        </div>
      ) : (
        <div className="space-y-2">
          {recommendations.map((rec) => {
            const confidencePct = rec.confidence
              ? `${(parseFloat(rec.confidence) * 100).toFixed(0)}%`
              : null;

            return (
              <div
                key={rec.id}
                className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs flex items-center justify-between gap-2"
              >
                <div>
                  <div className="text-[11px] text-slate-400">{getRecommendationTitle(rec.recommendation_type)}</div>
                  <div className="font-semibold text-slate-100 mt-0.5">{rec.recommended_value}</div>
                  <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                    Lineage: {rec.rule_name} (v{rec.rule_version}) • {rec.explanation}
                  </div>
                </div>

                {confidencePct && (
                  <span className="font-mono text-xs text-emerald-400 font-semibold px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-900">
                    {confidencePct}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
