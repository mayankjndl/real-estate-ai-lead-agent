'use client'

import { useState } from 'react'
import { User, Building2, SlidersHorizontal, Bell, Save, Check } from 'lucide-react'

const TABS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'workspace', label: 'Workspace', icon: Building2 },
  { id: 'ai', label: 'AI Thresholds', icon: SlidersHorizontal },
  { id: 'notifications', label: 'Notifications', icon: Bell },
]

// Custom hook: reads from localStorage on mount, falls back to defaultValue
function usePersistentState<T>(key: string, defaultValue: T): [T, React.Dispatch<React.SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => {
    if (typeof window === 'undefined') return defaultValue
    try {
      const stored = localStorage.getItem(key)
      return stored !== null ? (JSON.parse(stored) as T) : defaultValue
    } catch {
      return defaultValue
    }
  })
  return [value, setValue]
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
        checked ? 'bg-emerald-500' : 'bg-zinc-700'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

function Section({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <div className="bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-6 space-y-6">
      <div className="border-b border-zinc-800 pb-4">
        <h2 className="text-base font-semibold text-white">{title}</h2>
        <p className="text-sm text-zinc-400 mt-0.5">{description}</p>
      </div>
      {children}
    </div>
  )
}

function FieldRow({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
      <div>
        <p className="text-sm font-medium text-zinc-200">{label}</p>
        {hint && <p className="text-xs text-zinc-500 mt-0.5">{hint}</p>}
      </div>
      <div className="sm:w-64">{children}</div>
    </div>
  )
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile')
  const [saved, setSaved] = useState(false)

  // Profile state — persisted
  const [displayName, setDisplayName] = usePersistentState('settings_displayName', 'Admin')
  const [company, setCompany] = usePersistentState('settings_company', 'Revenue OS HQ')

  // Workspace preferences — persisted
  const [defaultView, setDefaultView] = usePersistentState('settings_defaultView', 'dashboard')
  const [leadsPerPage, setLeadsPerPage] = usePersistentState('settings_leadsPerPage', '25')

  // Notification toggles — persisted
  const [emailDigest, setEmailDigest] = usePersistentState('settings_emailDigest', true)
  const [whatsappAlerts, setWhatsappAlerts] = usePersistentState('settings_whatsappAlerts', true)
  const [newLeadNotif, setNewLeadNotif] = usePersistentState('settings_newLeadNotif', true)
  const [weeklyReport, setWeeklyReport] = usePersistentState('settings_weeklyReport', false)

  const handleSave = () => {
    // Persist all current state values to localStorage
    localStorage.setItem('settings_displayName', JSON.stringify(displayName))
    localStorage.setItem('settings_company', JSON.stringify(company))
    localStorage.setItem('settings_defaultView', JSON.stringify(defaultView))
    localStorage.setItem('settings_leadsPerPage', JSON.stringify(leadsPerPage))
    localStorage.setItem('settings_emailDigest', JSON.stringify(emailDigest))
    localStorage.setItem('settings_whatsappAlerts', JSON.stringify(whatsappAlerts))
    localStorage.setItem('settings_newLeadNotif', JSON.stringify(newLeadNotif))
    localStorage.setItem('settings_weeklyReport', JSON.stringify(weeklyReport))

    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div className="space-y-8 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-white tracking-tight">Settings</h1>
        <p className="text-sm text-zinc-400 mt-1">Manage your workspace preferences and account configuration.</p>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 bg-zinc-900/60 border border-zinc-800 rounded-xl p-1 w-fit flex-wrap">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
              activeTab === id
                ? 'bg-zinc-800 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab: Profile */}
      {activeTab === 'profile' && (
        <Section title="Profile Settings" description="Update your personal information and display name.">
          <FieldRow label="Display Name" hint="Shown in the dashboard header and reports.">
            <input
              type="text"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500/70 transition"
            />
          </FieldRow>
          <FieldRow label="Email Address" hint="Managed by your system administrator.">
            <input
              type="email"
              value="admin@revenueos.com"
              readOnly
              className="w-full bg-zinc-900 border border-zinc-800 text-zinc-500 text-sm rounded-lg px-3 py-2 cursor-not-allowed"
            />
          </FieldRow>
          <FieldRow label="Company / Agency Name" hint="Displayed on exported reports and PDF summaries.">
            <input
              type="text"
              value={company}
              onChange={e => setCompany(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500/70 transition"
            />
          </FieldRow>
          <div className="flex justify-end pt-2">
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 text-sm font-semibold transition-all duration-150"
            >
              {saved ? <><Check className="w-4 h-4" /> Saved!</> : <><Save className="w-4 h-4" /> Save Profile</>}
            </button>
          </div>
        </Section>
      )}

      {/* Tab: Workspace */}
      {activeTab === 'workspace' && (
        <Section title="Workspace Preferences" description="Configure how your dashboard behaves by default.">
          <FieldRow label="Default View" hint="The page you land on after logging in.">
            <select
              value={defaultView}
              onChange={e => setDefaultView(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500/70 transition"
            >
              <option value="dashboard">Dashboard (Analytics)</option>
              <option value="leads">Lead Inbox</option>
              <option value="crm">CRM Pipeline</option>
            </select>
          </FieldRow>
          <FieldRow label="Leads Per Page" hint="Number of leads displayed in the Lead Inbox table.">
            <select
              value={leadsPerPage}
              onChange={e => setLeadsPerPage(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500/70 transition"
            >
              <option value="10">10 leads</option>
              <option value="25">25 leads</option>
              <option value="50">50 leads</option>
              <option value="100">100 leads</option>
            </select>
          </FieldRow>
          <div className="flex justify-end pt-2">
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 text-sm font-semibold transition-all duration-150"
            >
              {saved ? <><Check className="w-4 h-4" /> Saved!</> : <><Save className="w-4 h-4" /> Save Preferences</>}
            </button>
          </div>
        </Section>
      )}

      {/* Tab: AI Thresholds */}
      {activeTab === 'ai' && (
        <Section title="AI Scoring Thresholds" description="The active ML conversion thresholds governing lead temperature classification.">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-red-500/5 border border-red-500/20 rounded-xl">
              <div className="flex items-center gap-3">
                <span className="w-3 h-3 rounded-full bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.7)] animate-pulse" />
                <div>
                  <p className="text-sm font-semibold text-white">Hot Lead</p>
                  <p className="text-xs text-zinc-400">High-intent buyer, immediate follow-up required</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-red-400">≥ 82%</p>
                <p className="text-xs text-zinc-500">Conversion Probability</p>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-amber-500/5 border border-amber-500/20 rounded-xl">
              <div className="flex items-center gap-3">
                <span className="w-3 h-3 rounded-full bg-amber-400" />
                <div>
                  <p className="text-sm font-semibold text-white">Warm Lead</p>
                  <p className="text-xs text-zinc-400">Active engagement, scheduled nurture sequence</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-amber-400">≥ 55%</p>
                <p className="text-xs text-zinc-500">Conversion Probability</p>
              </div>
            </div>

            <div className="flex items-center justify-between p-4 bg-zinc-800/50 border border-zinc-700/50 rounded-xl">
              <div className="flex items-center gap-3">
                <span className="w-3 h-3 rounded-full bg-zinc-500" />
                <div>
                  <p className="text-sm font-semibold text-white">Cold Lead</p>
                  <p className="text-xs text-zinc-400">Low intent, passive 48h re-engagement sequence</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-zinc-400">&lt; 55%</p>
                <p className="text-xs text-zinc-500">Conversion Probability</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 p-3 bg-zinc-800/40 border border-zinc-700/50 rounded-lg mt-2">
            <SlidersHorizontal className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <p className="text-xs text-zinc-400">
              These thresholds are managed by the AI configuration layer. Contact your AI Automation Owner to request adjustments.
            </p>
          </div>
        </Section>
      )}

      {/* Tab: Notifications */}
      {activeTab === 'notifications' && (
        <Section title="Notification Controls" description="Configure how and when you receive lead activity alerts.">
          <FieldRow label="New Lead Alert" hint="Get notified instantly when a new lead is captured.">
            <div className="flex justify-end">
              <Toggle checked={newLeadNotif} onChange={setNewLeadNotif} />
            </div>
          </FieldRow>
          <FieldRow label="WhatsApp Follow-Up Alerts" hint="Receive alerts when automated follow-ups are dispatched.">
            <div className="flex justify-end">
              <Toggle checked={whatsappAlerts} onChange={setWhatsappAlerts} />
            </div>
          </FieldRow>
          <FieldRow label="Daily Email Digest" hint="A morning summary of all leads captured in the last 24 hours.">
            <div className="flex justify-end">
              <Toggle checked={emailDigest} onChange={setEmailDigest} />
            </div>
          </FieldRow>
          <FieldRow label="Weekly Performance Report" hint="A Friday summary with ROI metrics and conversion rates.">
            <div className="flex justify-end">
              <Toggle checked={weeklyReport} onChange={setWeeklyReport} />
            </div>
          </FieldRow>
          <div className="flex justify-end pt-2">
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 text-sm font-semibold transition-all duration-150"
            >
              {saved ? <><Check className="w-4 h-4" /> Saved!</> : <><Save className="w-4 h-4" /> Save Notifications</>}
            </button>
          </div>
        </Section>
      )}
    </div>
  )
}
