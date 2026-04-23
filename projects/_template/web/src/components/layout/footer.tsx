import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 py-6 text-sm text-muted-foreground sm:flex-row">
        <p>
          Built on{" "}
          <Link href="https://sastaspace.com" className="underline-offset-4 hover:underline">
            sastaspace.com
          </Link>
        </p>
        <p>
          {new Date().getFullYear()} &middot;{" "}
          <Link href="/contact" className="underline-offset-4 hover:underline">
            Contact
          </Link>
        </p>
      </div>
    </footer>
  );
}
