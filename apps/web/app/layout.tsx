import './globals.css'
import React from 'react'

export const metadata = {
  title: 'Recs Web',
  description: 'Personalised TV Recommender',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">{children}</body>
    </html>
  )
}

