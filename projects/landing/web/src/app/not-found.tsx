import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";

export const metadata = {
  title: "nothing here — sastaspace",
};

export default function NotFound() {
  return (
    <AppShell>
      <section className="mx-auto max-w-2xl px-6 pb-24 pt-20 sm:px-8">
        <div className="font-mono text-xs tracking-[0.08em] text-muted-foreground">
          404 · nothing here
        </div>
        <h1 className="mt-5 text-[32px] font-medium leading-[1.1] tracking-[-0.02em] sm:text-[42px]">
          Nothing here.
        </h1>
        <p className="mt-6 text-[17px] leading-relaxed text-foreground/85">
          The workshop&apos;s this way. Try the{" "}
          <Link href="/" className="text-[var(--brand-sasta-text)] underline-offset-4 hover:underline">
            homepage
          </Link>.
        </p>
      </section>
    </AppShell>
  );
}
