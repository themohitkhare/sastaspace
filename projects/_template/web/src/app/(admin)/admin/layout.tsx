import { redirect } from "next/navigation";
import { isCurrentUserAdmin, getSessionUser } from "@/lib/supabase/auth-helpers";
import { Topbar } from "@/components/layout/topbar";
import { Sidebar } from "@/components/layout/sidebar";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const user = await getSessionUser();
  if (!user) redirect("/sign-in?next=/admin");
  const admin = await isCurrentUserAdmin();
  if (!admin) redirect("/?error=not_authorized");

  return (
    <div className="flex min-h-screen flex-col">
      <Topbar projectName="__NAME__" />
      <div className="flex flex-1">
        <Sidebar
          title="Admin"
          items={[
            { href: "/admin", label: "Overview", icon: "dashboard" },
            { href: "/admin/users", label: "Users", icon: "users" },
          ]}
        />
        <div className="flex-1 p-6">{children}</div>
      </div>
    </div>
  );
}
