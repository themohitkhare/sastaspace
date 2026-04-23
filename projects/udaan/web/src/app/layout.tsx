import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Noto_Sans_Devanagari } from "next/font/google";
import { ThemeProvider } from "@/components/theme/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

const notoDeva = Noto_Sans_Devanagari({
  subsets: ["devanagari", "latin"],
  weight: ["400", "500"],
  variable: "--font-noto-deva",
  display: "swap",
});

export const metadata: Metadata = {
  title: "udaan — what to expect on your flight",
  description:
    "Tell udaan where and when you're flying. It tells you the risk of delay, cancellation, and baggage trouble — from DGCA data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${jetbrainsMono.variable} ${notoDeva.variable}`}
    >
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          {children}
          <Toaster richColors closeButton position="top-right" />
        </ThemeProvider>
      </body>
    </html>
  );
}
