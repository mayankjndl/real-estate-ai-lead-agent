'use client'

import React, { useState, useEffect } from 'react'
import { Plus, X, Users, Briefcase, MapPin, Loader2 } from 'lucide-react'

// Basic UI types
interface Agent {
  id: number;
  name: string;
  email: string;
  phone: string;
  is_manager: boolean;
  is_director?: boolean;
  locations?: string;
  speciality?: string;
  deal_size?: string;
  lead_type?: string;
}

export default function TeamManagementPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  
  // Form State
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    is_manager: false,
    is_director: false,
    locations: '',
    speciality: '',
    deal_size: '',
    lead_type: ''
  })

  const fetchAgents = async () => {
    try {
      const token = document.cookie.split('; ').find(row => row.startsWith('jwt='))?.split('=')[1] || '';
      
      const res = await fetch('/api/v1/agents', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (res.ok) {
        const data = await res.json()
        setAgents(data.agents || data || [])
      }
    } catch (err) {
      console.error('Failed to fetch agents', err)
    } finally {
      setLoading(false)
    }
  }

  // Fetch agents on mount
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- false positive: fetchAgents sets state only in async continuations after `await`, never synchronously in the effect body
    fetchAgents()
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target
    const checked = (e.target as HTMLInputElement).checked
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      const token = document.cookie.split('; ').find(row => row.startsWith('jwt='))?.split('=')[1] || '';
      const res = await fetch('/api/v1/agents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      })

      if (res.ok) {
        setIsModalOpen(false)
        setFormData({
          name: '',
          phone: '',
          email: '',
          is_manager: false,
          is_director: false,
          locations: '',
          speciality: '',
          deal_size: '',
          lead_type: ''
        })
        setLoading(true)
        fetchAgents()
      } else {
        alert('Failed to add team member.')
      }
    } catch (err) {
      console.error('Error adding agent', err)
      alert('An error occurred.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Users className="w-6 h-6 text-indigo-400" />
            Agent Management
          </h1>
          <p className="text-gray-400 mt-1 text-sm">
            Manage your sales team, managers, and specialized agents.
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Add Team Member
        </button>
      </div>

      {/* Agents Grid/Table */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
        </div>
      ) : agents.length === 0 ? (
        <div className="text-center py-20 bg-gray-900/50 rounded-xl border border-gray-800">
          <Users className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-white mb-1">No agents found</h3>
          <p className="text-gray-400 text-sm">Add your first team member to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <div key={agent.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-base font-semibold text-white">{agent.name}</h3>
                  <p className="text-sm text-gray-400">{agent.email}</p>
                </div>
                {agent.is_manager && (
                  <span className="px-2.5 py-1 bg-indigo-500/10 text-indigo-400 text-xs font-medium rounded-full border border-indigo-500/20">
                    Manager
                  </span>
                )}
                {agent.is_director && (
                  <span className="px-2.5 py-1 bg-rose-500/10 text-rose-400 text-xs font-medium rounded-full border border-rose-500/20">
                    Director
                  </span>
                )}
              </div>
              
              <div className="space-y-2 mt-4 pt-4 border-t border-gray-800 text-sm text-gray-400">
                <div className="flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-gray-500" />
                  <span>{agent.speciality ? agent.speciality.replace('_', ' ') : 'Generalist'}</span>
                </div>
                {agent.locations && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-gray-500" />
                    <span className="truncate">{agent.locations}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Agent Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-lg shadow-2xl my-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-800">
              <h2 className="text-lg font-semibold text-white">Add Team Member</h2>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-white transition-colors p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5 md:col-span-2">
                  <label className="text-sm font-medium text-gray-300">Full Name *</label>
                  <input
                    type="text"
                    name="name"
                    required
                    value={formData.name}
                    onChange={handleInputChange}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    placeholder="e.g. Sarah Connor"
                  />
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-gray-300">Phone *</label>
                  <input
                    type="tel"
                    name="phone"
                    required
                    value={formData.phone}
                    onChange={handleInputChange}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    placeholder="+91 9876543210"
                  />
                </div>
                
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-gray-300">Email *</label>
                  <input
                    type="email"
                    name="email"
                    required
                    value={formData.email}
                    onChange={handleInputChange}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    placeholder="sarah@example.com"
                  />
                </div>
              </div>

              <div className="pt-2">
                <label className="flex items-center gap-3 cursor-pointer p-3 rounded-lg border border-gray-800 bg-gray-950/50 hover:bg-gray-800/50 transition-colors">
                  <input
                    type="checkbox"
                    name="is_manager"
                    checked={formData.is_manager}
                    onChange={handleInputChange}
                    className="w-4 h-4 rounded bg-gray-900 border-gray-700 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-gray-900"
                  />
                  <div>
                    <span className="text-sm font-medium text-white block">Manager Privileges</span>
                    <span className="text-xs text-gray-400 block mt-0.5">Can view all team leads and metrics</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 cursor-pointer p-3 rounded-lg border border-gray-800 bg-gray-950/50 hover:bg-gray-800/50 transition-colors">
                  <input
                    type="checkbox"
                    name="is_director"
                    checked={formData.is_director}
                    onChange={handleInputChange}
                    className="w-4 h-4 rounded bg-gray-900 border-gray-700 text-rose-600 focus:ring-rose-500 focus:ring-offset-gray-900"
                  />
                  <div>
                    <span className="text-sm font-medium text-white block">Director (30m Escalation)</span>
                    <span className="text-xs text-gray-400 block mt-0.5">Receives critical 30-minute unacknowledged lead alerts</span>
                  </div>
                </label>
              </div>

              <div className="border-t border-gray-800 pt-5 space-y-4">
                <h3 className="text-sm font-medium text-indigo-400 uppercase tracking-wider">AI Routing Preferences (Optional)</h3>
                
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-gray-300">Assigned Locations</label>
                  <input
                    type="text"
                    name="locations"
                    value={formData.locations}
                    onChange={handleInputChange}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    placeholder="Enter comma-separated areas, e.g., Baner, Wakad, Balewadi"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-gray-300">Speciality</label>
                    <select
                      name="speciality"
                      value={formData.speciality}
                      onChange={handleInputChange}
                      className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    >
                      <option value="">Any</option>
                      <option value="luxury">Luxury</option>
                      <option value="mid_range">Mid Range</option>
                      <option value="investment">Investment</option>
                      <option value="rental">Rental</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-gray-300">Deal Size</label>
                    <select
                      name="deal_size"
                      value={formData.deal_size}
                      onChange={handleInputChange}
                      className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    >
                      <option value="">Any</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-gray-300">Lead Type</label>
                    <select
                      name="lead_type"
                      value={formData.lead_type}
                      onChange={handleInputChange}
                      className="w-full bg-gray-950 border border-gray-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500"
                    >
                      <option value="">Any</option>
                      <option value="buyer">Buyer</option>
                      <option value="tenant">Tenant</option>
                      <option value="investor">Investor</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 pt-4 border-t border-gray-800 mt-6">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-4 py-2.5 bg-transparent border border-gray-700 hover:bg-gray-800 text-white rounded-lg transition-colors text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  {submitting ? 'Saving...' : 'Add Team Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
