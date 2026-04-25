import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: "notes — sastaspace",
  description: "Workshop notes from the sastaspace lab. Thinking out loud.",
  metadataBase: new URL("https://notes.sastaspace.com"),
  openGraph: {
    title: "notes — sastaspace",
    description: "Workshop notes from the sastaspace lab.",
    url: "https://notes.sastaspace.com",
    siteName: "sastaspace notes",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body>{children}</body>
    </html>
  );
}
