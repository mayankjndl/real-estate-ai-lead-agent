import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Revenue OS | AI Real Estate Lead Intelligence",
    template: "%s | Revenue OS",
  },
  description:
    "Revenue OS by Imperion Data Systems. The AI-powered lead intelligence platform built for modern real estate agencies. Capture, score, and convert WhatsApp leads in real time.",
  metadataBase: new URL("https://real-estate-ai-lead-agent-5q20tzn22.vercel.app"),
  openGraph: {
    title: "Revenue OS | AI Real Estate Lead Intelligence",
    description:
      "AI-powered lead intelligence platform for modern real estate agencies. Built by Imperion Data Systems.",
    siteName: "Revenue OS",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Revenue OS | AI Real Estate Lead Intelligence",
    description:
      "AI-powered lead intelligence platform for modern real estate agencies. Built by Imperion Data Systems.",
  },
  keywords: [
    "real estate AI",
    "lead intelligence",
    "WhatsApp CRM",
    "SaaS dashboard",
    "Imperion Data Systems",
    "Revenue OS",
    "lead scoring",
  ],
  authors: [{ name: "Imperion Data Systems" }],
  creator: "Imperion Data Systems",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
