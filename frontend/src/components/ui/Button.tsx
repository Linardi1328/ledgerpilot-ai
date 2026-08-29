import React from "react";
import { clsx } from "clsx";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "warning" | "outline" | "subtle";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "secondary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseClasses =
      "inline-flex items-center justify-center font-medium rounded transition focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed";

    const variantClasses = {
      primary: "bg-blue-600 hover:bg-blue-500 text-white focus:ring-blue-500 shadow-sm",
      secondary: "bg-slate-800 hover:bg-slate-700 text-slate-200 focus:ring-slate-500 border border-slate-700",
      danger: "bg-rose-600 hover:bg-rose-500 text-white focus:ring-rose-500 shadow-sm",
      warning: "bg-amber-600 hover:bg-amber-500 text-white focus:ring-amber-500 shadow-sm",
      outline: "bg-transparent hover:bg-slate-800/60 text-slate-300 border border-slate-700 focus:ring-slate-500",
      subtle: "bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200 focus:ring-slate-500",
    };

    const sizeClasses = {
      sm: "px-2.5 py-1 text-xs",
      md: "px-3.5 py-1.5 text-xs",
      lg: "px-5 py-2 text-sm font-semibold",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={clsx(baseClasses, variantClasses[variant], sizeClasses[size], className)}
        {...props}
      >
        {isLoading && (
          <span className="w-3.5 h-3.5 mr-1.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
