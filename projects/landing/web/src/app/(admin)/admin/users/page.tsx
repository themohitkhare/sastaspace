import { createClient } from "@/lib/supabase/server";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const metadata = { title: "Users — Admin — SastaSpace" };

type AdminRow = {
  email: string;
  note: string | null;
  added_at: string;
};

export default async function AdminUsersPage() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("admins")
    .select("email, note, added_at")
    .order("added_at", { ascending: true });

  const rows = (data ?? []) as AdminRow[];

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Admins</h1>
        <p className="text-sm text-muted-foreground">
          Emails in this list can access the /admin area. Add or remove via Studio.
        </p>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Note</TableHead>
              <TableHead className="text-right">Added</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="h-20 text-center text-muted-foreground">
                  No admins found. Run migrations to seed.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow key={row.email}>
                  <TableCell className="font-medium">{row.email}</TableCell>
                  <TableCell className="text-muted-foreground">{row.note ?? "—"}</TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {new Date(row.added_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
