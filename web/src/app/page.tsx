import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-background text-foreground">
      <h1 className="text-4xl font-bold mb-4">SastaSpace</h1>
      <p className="text-muted-foreground mb-8">AI Website Redesigner</p>
      <Button size="lg">Coming Soon</Button>
    </main>
  );
}
