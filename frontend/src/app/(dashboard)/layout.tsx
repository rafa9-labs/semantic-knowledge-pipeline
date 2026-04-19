"use client";

import { CurriculumSidebar } from "@/components/layout/CurriculumSidebar";
import { AiTutor } from "@/components/layout/AiTutor";
import Link from "next/link";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-screen grid grid-cols-[280px_1fr_350px]">
      <CurriculumSidebar />
      <main className="flex flex-col overflow-hidden border-x border-border">
        <header className="flex items-center justify-between border-b border-border px-6 py-3">
          <Link href="/dashboard" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
            KodaStudy
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link href="/generate" className="text-muted-foreground hover:text-foreground transition-colors">Generate</Link>
            <Link href="/settings" className="text-muted-foreground hover:text-foreground transition-colors">Settings</Link>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto p-6">{children}</div>
      </main>
      <AiTutor />
    </div>
  );
}
