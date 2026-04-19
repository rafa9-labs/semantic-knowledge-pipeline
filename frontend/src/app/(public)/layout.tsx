export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border px-6 py-4">
        <nav className="mx-auto flex max-w-7xl items-center justify-between">
          <a href="/" className="text-xl font-bold tracking-tight">
            KodaStudy
          </a>
          <div className="flex items-center gap-6 text-sm">
            <a href="/catalog" className="text-muted-foreground hover:text-foreground transition-colors">Catalog</a>
            <a href="/pricing" className="text-muted-foreground hover:text-foreground transition-colors">Pricing</a>
            <a href="/login" className="text-muted-foreground hover:text-foreground transition-colors">Log in</a>
            <a href="/signup" className="rounded-lg bg-primary px-4 py-2 text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors">Sign up</a>
          </div>
        </nav>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}
