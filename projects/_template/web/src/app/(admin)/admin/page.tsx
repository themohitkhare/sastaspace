import { getSessionUser } from "@/lib/supabase/auth-helpers";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata = { title: "Admin — __NAME__" };

export default async function AdminOverviewPage() {
  const user = await getSessionUser();
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-3xl font-medium tracking-tight">The back room.</h1>
        <p className="mt-2 text-sm text-muted-foreground">Signed in as {user?.email}.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Data</CardTitle>
            <CardDescription>Browse tables in Supabase Studio.</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Open{" "}
            <a
              href="https://studio.sastaspace.com"
              target="_blank"
              rel="noreferrer"
              className="underline-offset-4 hover:underline"
            >
              studio.sastaspace.com
            </a>
            .
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Users</CardTitle>
            <CardDescription>See who has signed up.</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Open the{" "}
            <a href="/admin/users" className="underline-offset-4 hover:underline">
              users page
            </a>
            .
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
