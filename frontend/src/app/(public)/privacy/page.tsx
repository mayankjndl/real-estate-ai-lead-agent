export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-white pt-24 pb-20 px-6 font-sans">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold tracking-tight mb-8">Privacy Policy</h1>
        <p className="text-sm text-slate-500 dark:text-zinc-400 mb-12">
          Last updated: {new Date().toLocaleDateString()}
        </p>
        
        <div className="space-y-8 text-slate-700 dark:text-zinc-300 leading-relaxed">
          <section>
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">1. Information We Collect</h2>
            <p>
              Imperion Data Systems Private Limited ("we", "our", or "us") operates Revenue OS. We collect information that you provide directly to us, including your name, email address, phone number, and any other information you choose to provide when using our platform.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">2. How We Use Your Information</h2>
            <p className="mb-4">We use the information we collect to:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Provide, maintain, and improve our services.</li>
              <li>Process and complete transactions.</li>
              <li>Send administrative information, including updates, security alerts, and support messages.</li>
              <li>Respond to your comments, questions, and requests.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">3. AI Data Processing</h2>
            <p>
              As an AI-driven platform, Revenue OS processes conversational data (such as WhatsApp messages) to score and qualify leads. This data is securely processed and is solely used to provide services to the respective client account. We do not sell conversational data to third parties.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">4. Contact Us</h2>
            <p>
              If you have any questions about this Privacy Policy, please contact us at: <br/>
              <strong>Imperion Data Systems Private Limited</strong><br/>
              Email: info.imperiondatasystem@gmail.com
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
