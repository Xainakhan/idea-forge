import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Idealist",
  description: "Generate distinct software business ideas.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
