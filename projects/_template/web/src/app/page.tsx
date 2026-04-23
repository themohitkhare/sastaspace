import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Page() {
  return (
    <AppShell projectName="__NAME__">
      <section className="border-b">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:py-28">
          <p className="mb-6 font-mono text-xs tracking-[0.08em] text-muted-foreground">
            ~/mohit · __NAME__.sastaspace.com
          </p>
          <h1 className="max-w-3xl text-4xl font-medium tracking-tight sm:text-5xl">
            __NAME__
          </h1>
          <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
            A project on sastaspace.com. Replace this copy with what the project does and why it
            exists.
          </p>
          <div className="mt-8 flex gap-3">
            <Button asChild>
              <Link href="/contact">
                Get in touch
                <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="https://sastaspace.com">All projects</Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Fast</CardTitle>
              <CardDescription>Next.js App Router with streaming and RSC.</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Built-in SSR, edge-ready by default.
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Data</CardTitle>
              <CardDescription>Postgres + PostgREST shared across projects.</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              50+ extensions via supabase/postgres.
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Auth</CardTitle>
              <CardDescription>GoTrue + RLS, opt-in per project.</CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Same JWT secret as PostgREST.
            </CardContent>
          </Card>
        </div>
      </section>
    </AppShell>
  );
}
