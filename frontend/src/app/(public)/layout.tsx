import Header from '@/components/Header'

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <>
      <Header />
      <div className="pt-16">
        {children}
      </div>
    </>
  )
}
