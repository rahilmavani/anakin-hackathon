import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TenderFlow",
  description: "AI-native tender discovery for Indian SMBs",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
