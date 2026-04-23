import { Topbar } from "@/components/layout/topbar";
import { Footer } from "@/components/layout/footer";

export function AppShell({
  children,
}: {
  children: React.ReactNode;
  /** Reserved for future per-project branding. Currently unused on sastaspace.com itself. */
  projectName?: string;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <Topbar />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
