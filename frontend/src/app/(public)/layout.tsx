import Header from '@/components/Header'
import Footer from '@/components/Footer'
import { ThemeProvider } from "@/components/ThemeProvider"

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" storageKey="public-theme" enableSystem={false}>
      <div className="flex flex-col min-h-screen">
        <Header />
        <main className="flex-grow pt-16">
          {children}
        </main>
        <Footer />
      </div>
    </ThemeProvider>
  )
}
