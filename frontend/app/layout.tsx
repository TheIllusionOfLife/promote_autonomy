import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Promote Autonomy',
  description: 'AI-powered marketing automation with human approval',
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
