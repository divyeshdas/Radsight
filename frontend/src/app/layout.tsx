import type { Metadata } from "next";
import Script from "next/script";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "RadSight — AI Radiology Intelligence",
  description: "AI-powered radiology report analysis, clinical risk prioritization, and healthcare analytics platform",
  keywords: ["radiology", "AI", "clinical decision support", "medical imaging", "healthcare analytics"],
};

const themeScript = `
  (function() {
    var theme = localStorage.getItem('radsight-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
  })();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="antialiased" style={{ backgroundColor: "var(--bg-primary)", color: "var(--text-primary)" }}>
        {children}
      </body>
    </html>
  );
}
