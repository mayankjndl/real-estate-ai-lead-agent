export default function TermsPage() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-white pt-24 pb-20 px-6 font-sans">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold tracking-tight mb-8">Terms of Service</h1>
        <p className="text-sm text-slate-500 dark:text-zinc-400 mb-12">
          Last updated: {new Date().toLocaleDateString()}
        </p>
        
        <div className="space-y-8 text-slate-700 dark:text-zinc-300 leading-relaxed">
          <section>
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">1. Acceptance of Terms</h2>
            <p>
              By accessing and using Revenue OS, a product of Imperion Data Systems Private Limited, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our services.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">2. Description of Service</h2>
            <p>
              Revenue OS provides an AI-powered lead intelligence and automation platform tailored for the real estate industry. We offer tools for capturing, qualifying, and managing leads via AI agents. The dashboard access and specific API quotas are governed by the subscription plan you choose.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">3. User Responsibilities</h2>
            <p className="mb-4">As a user of our platform, you agree to:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Provide accurate and complete registration information.</li>
              <li>Maintain the security of your account credentials.</li>
              <li>Ensure your use of the platform complies with all applicable local, state, and international laws, including data privacy regulations (e.g., GDPR, CCPA).</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">4. Intellectual Property</h2>
            <p>
              The platform, including its original content, features, and functionality, are owned by Imperion Data Systems Private Limited and are protected by international copyright, trademark, and intellectual property laws. You may not copy, modify, or distribute our source code or proprietary AI models.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">5. Contact Us</h2>
            <p>
              If you have any questions regarding these Terms, please reach out to:<br/>
              <strong>Imperion Data Systems Private Limited</strong><br/>
              Website: www.imperiondata.com
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
