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
      <Topbar projectName={projectName} />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
