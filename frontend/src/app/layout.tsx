import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/context/AuthContext";
import { ClientProvider } from "@/lib/context/ClientContext";
import { AppShell } from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: "LedgerPilot AI - Phase 5 Human Review Workspace",
  description: "Attributable AI-assisted accounting and double-entry review platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen">
        <AuthProvider>
          <ClientProvider>
            <AppShell>{children}</AppShell>
          </ClientProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
