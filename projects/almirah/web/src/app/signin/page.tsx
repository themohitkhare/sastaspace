import { redirect } from "next/navigation";

// Almirah doesn't run its own sign-in UI — everything funnels through the
// central sastaspace.com sign-in so one flow serves every subdomain. After
// auth, the session cookie (scoped to .sastaspace.com) is already visible
// here.
export default async function SignIn({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const { next } = await searchParams;
  const safeNext = next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
  const returnUrl = `https://almirah.sastaspace.com${safeNext}`;
  redirect(
    `https://sastaspace.com/sign-in?next=${encodeURIComponent(returnUrl)}`,
  );
}
