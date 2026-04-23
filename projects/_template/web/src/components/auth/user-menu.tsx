import Link from "next/link";
import { Button } from "@/components/ui/button";

export function UserMenu() {
  return (
    <Button asChild variant="outline" size="sm">
      <Link href="/sign-in">Sign in</Link>
    </Button>
  );
}
