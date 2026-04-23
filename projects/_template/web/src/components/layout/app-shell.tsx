import { Topbar } from "@/components/layout/topbar";
import { Footer } from "@/components/layout/footer";

export function AppShell({
  children,
  projectName,
}: {
  children: React.ReactNode;
  projectName?: string;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-[var(--brand-ink)] focus:px-3 focus:py-2 focus:text-[var(--brand-paper)]"
      >
        Skip to content
      </a>
      <Topbar projectName={projectName} />
      <main id="main" className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
