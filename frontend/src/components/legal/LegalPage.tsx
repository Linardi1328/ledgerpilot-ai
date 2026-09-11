import Link from "next/link";
import type { ReactNode } from "react";

export type LegalSection = {
  title: string;
  body?: ReactNode;
  items?: readonly ReactNode[];
};

const links = [
  ["Privacy", "/privacy"],
  ["Terms", "/terms"],
  ["Cookies", "/cookies"],
  ["Payments & refunds", "/refunds"],
] as const;

export function LegalPage({
  title,
  summary,
  sections,
}: {
  title: string;
  summary: ReactNode;
  sections: readonly LegalSection[];
}) {
  return (
    <article className="mx-auto max-w-4xl space-y-8 py-4" aria-labelledby="legal-title">
      <header className="space-y-3 border-b border-slate-800 pb-6">
        <p className="text-xs font-mono uppercase tracking-wider text-blue-300">LedgerPilot AI · Development prototype</p>
        <h1 id="legal-title" className="text-3xl font-bold text-slate-50">{title}</h1>
        <div className="max-w-3xl text-sm leading-7 text-slate-300">{summary}</div>
        <p className="text-xs text-slate-500">Effective: 11 September 2026</p>
        <nav aria-label="Legal policies" className="flex flex-wrap gap-x-4 gap-y-2 text-xs">
          {links.map(([label, href]) => (
            <Link key={href} href={href} className="text-blue-300 underline underline-offset-4 hover:text-blue-200">
              {label}
            </Link>
          ))}
        </nav>
      </header>

      <div className="space-y-7">
        {sections.map((section) => (
          <section key={section.title} className="space-y-2">
            <h2 className="text-lg font-semibold text-slate-100">{section.title}</h2>
            {section.body ? <div className="text-sm leading-7 text-slate-300">{section.body}</div> : null}
            {section.items?.length ? (
              <ul className="list-disc space-y-2 pl-5 text-sm leading-7 text-slate-300">
                {section.items.map((item, index) => <li key={index}>{item}</li>)}
              </ul>
            ) : null}
          </section>
        ))}
      </div>

      <aside className="rounded-lg border border-amber-800/70 bg-amber-950/30 p-4 text-xs leading-6 text-amber-200">
        Production use is not authorised by these website policies. Real-client deployment requires a separate legal/privacy, security, retention, data-processing, and professional-practice review.
      </aside>
    </article>
  );
}
