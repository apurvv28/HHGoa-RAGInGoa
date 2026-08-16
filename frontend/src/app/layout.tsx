import './globals.css';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'HH Goa 2026 — Voice RAG System (Team TechTadkaa)',
  description: 'Voice-Enabled RAG System for MSMARCO-XI Indic Multilingual Corpus',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#075E34] text-[#FEFCE8] antialiased selection:bg-[#FFE500] selection:text-[#044425]">
        {children}
      </body>
    </html>
  );
}
