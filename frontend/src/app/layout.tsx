import './globals.css';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'HH Goa 2026 — Voice RAG System',
  description: 'Sub-100ms Voice-Enabled RAG System for MSMARCO-XI Indic Multilingual Corpus (Team TechTadkaa)',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
