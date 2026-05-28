import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "RadSight — AI Radiology Intelligence",
  description: "AI-powered radiology report analysis, clinical risk prioritization, and healthcare analytics platform",
  keywords: ["radiology", "AI", "clinical decision support", "medical imaging", "healthcare analytics"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-background text-text-primary">
        {children}
      </body>
    </html>
  );
}
