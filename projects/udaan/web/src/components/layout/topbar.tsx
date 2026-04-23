import Link from "next/link";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { UserMenu } from "@/components/auth/user-menu";

export function Topbar({ projectName = "udaan" }: { projectName?: string }) {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="h-2 w-2 rounded-full bg-primary" />
          <span>{projectName}</span>
        </Link>
        <nav className="flex items-center gap-2">
          <Link
            href="/contact"
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            Contact
          </Link>
          <ThemeToggle />
          <UserMenu />
        </nav>
      </div>
    </header>
  );
}
