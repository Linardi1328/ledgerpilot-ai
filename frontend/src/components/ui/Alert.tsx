import React from "react";
import { AlertCircle, AlertTriangle, CheckCircle, Info } from "lucide-react";
import { clsx } from "clsx";

export interface AlertProps {
  variant?: "error" | "warning" | "info" | "success";
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function Alert({ variant = "info", title, children, className }: AlertProps) {
  const variantStyles = {
    error: "bg-rose-950/50 border-rose-800 text-rose-300",
    warning: "bg-amber-950/40 border-amber-800/80 text-amber-300",
    info: "bg-blue-950/40 border-blue-800/80 text-blue-300",
    success: "bg-emerald-950/40 border-emerald-800/80 text-emerald-300",
  };

  const icons = {
    error: <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />,
    warning: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />,
    info: <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />,
    success: <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />,
  };

  return (
    <div
      role="alert"
      className={clsx(
        "border rounded-lg p-3 text-xs flex items-start space-x-2.5",
        variantStyles[variant],
        className
      )}
    >
      {icons[variant]}
      <div className="flex-1 space-y-1">
        {title && <div className="font-semibold text-xs text-slate-100">{title}</div>}
        <div className="text-[11px] leading-relaxed text-slate-300">{children}</div>
      </div>
    </div>
  );
}

export function Card({
  title,
  action,
  subtitle,
  children,
  className,
}: {
  title?: React.ReactNode;
  action?: React.ReactNode;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={clsx("bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3", className)}>
      {(title || action) && (
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div>
            <div className="font-semibold text-xs text-slate-200 flex items-center space-x-2">{title}</div>
            {subtitle && <div className="text-[11px] text-slate-400 font-mono mt-0.5">{subtitle}</div>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div>{children}</div>
    </div>
  );
}
