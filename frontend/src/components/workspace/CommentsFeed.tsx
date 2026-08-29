import React, { useState } from "react";
import { ReviewCommentResponse } from "@/types/api";
import { ReviewCommentKind } from "@/types/roles";
import { MessageSquare, Send } from "lucide-react";

export function CommentsFeed({
  comments,
  onAddComment,
  canAddComment = true,
}: {
  comments: ReviewCommentResponse[];
  onAddComment?: (body: string) => Promise<void>;
  canAddComment?: boolean;
}) {
  const [commentText, setCommentText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim() || !onAddComment) return;

    try {
      setIsSubmitting(true);
      await onAddComment(commentText.trim());
      setCommentText("");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getKindBadge = (kind: ReviewCommentKind | string) => {
    switch (kind) {
      case ReviewCommentKind.ESCALATION_REASON:
      case "escalation_reason":
        return <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800">Escalation Reason</span>;
      case ReviewCommentKind.INFORMATION_REQUEST:
      case "information_request":
        return <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-purple-950 text-purple-300 border border-purple-800">Info Request</span>;
      case ReviewCommentKind.INFORMATION_RESPONSE:
      case "information_response":
        return <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">Info Response</span>;
      default:
        return <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">Review Note</span>;
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3 text-slate-100">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <span className="font-semibold text-xs text-slate-200 flex items-center space-x-1.5">
          <MessageSquare className="w-3.5 h-3.5 text-blue-400" />
          <span>Reviewer Internal Comments</span>
        </span>
        <span className="text-[10px] font-mono text-slate-500">Internal Discussion Only</span>
      </div>

      <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
        {comments.length === 0 ? (
          <div className="text-xs text-slate-500 italic p-3 text-center bg-slate-950/60 rounded border border-slate-800">
            No internal reviewer notes recorded.
          </div>
        ) : (
          comments.map((comment) => (
            <div key={comment.id} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-[11px] text-blue-400 font-semibold">
                    {comment.author_membership_id ? `User ${comment.author_membership_id.slice(0, 8)}` : "Reviewer"}
                  </span>
                  {getKindBadge(comment.kind)}
                </div>
                <span className="text-[10px] font-mono text-slate-500">
                  {new Date(comment.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>

              {/* Safe text rendering via normal React child expression */}
              <p className="text-[11px] text-slate-200 leading-relaxed font-sans">{comment.body}</p>
            </div>
          ))
        )}
      </div>

      {canAddComment && onAddComment && (
        <form onSubmit={handleSubmit} className="flex space-x-2 pt-1 border-t border-slate-800">
          <label htmlFor="internalCommentInput" className="sr-only">Internal Review Note</label>
          <input
            id="internalCommentInput"
            type="text"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder="Add internal reviewer note..."
            disabled={isSubmitting}
            className="flex-1 bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={!commentText.trim() || isSubmitting}
            className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold disabled:opacity-50 transition flex items-center space-x-1"
          >
            <Send className="w-3 h-3" />
            <span>Post</span>
          </button>
        </form>
      )}
    </div>
  );
}
