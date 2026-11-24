import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AuraTravel // Resilient Multi-Agent Travel Planner",
  description: "Collaborative multi-agent itinerary planner with LangGraph orchestration, synchronized swimlanes, and live disruption replanning.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-TW" className="dark">
      <body className="bg-slate-950 text-slate-100 antialiased selection:bg-brand-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
