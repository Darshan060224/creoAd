import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { getAuthHeader } from '../../lib/auth'

export default function InviteBoard() {
  const [members, setMembers] = useState([])
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('Editor')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const loadMembers = useCallback(async () => {
    try {
      const resp = await axios.get(`${API_URL}/api/users/team`, { headers: getAuthHeader() })
      setMembers(resp.data)
    } catch (err) {
      console.error('Failed to load team members', err)
    }
  }, [API_URL])

  useEffect(() => {
    loadMembers()
  }, [loadMembers])

  const handleSendInvite = async (e) => {
    e.preventDefault()
    if (!email) return
    setLoading(true)
    setError('')
    try {
      await axios.post(`${API_URL}/api/users/team/invite`, {
        email,
        role
      }, { headers: getAuthHeader() })
      setEmail('')
      loadMembers()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send invite')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section style={{ background: 'rgba(24, 24, 27, 0.6)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 20, padding: 20 }}>
      <h3 style={{ marginTop: 0 }}>Team invites</h3>
      <form onSubmit={handleSendInvite} style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="teammate@company.com"
          type="email"
          required
          style={{ flex: '1 1 240px', padding: 12, borderRadius: 12, border: '1px solid rgba(255, 255, 255, 0.1)', background: 'rgba(0, 0, 0, 0.3)', color: '#fff' }}
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          style={{ padding: 12, borderRadius: 12, border: '1px solid rgba(255, 255, 255, 0.1)', background: 'rgba(0, 0, 0, 0.5)', color: '#fff' }}
        >
          <option value="Editor">Editor</option>
          <option value="Viewer">Viewer</option>
          <option value="Admin">Admin</option>
        </select>
        <button
          type="submit"
          disabled={loading}
          style={{ padding: '12px 16px', borderRadius: 12, border: 'none', background: 'var(--accent)', color: '#fff', fontWeight: 800, cursor: 'pointer' }}
        >
          {loading ? 'Sending...' : 'Send invite'}
        </button>
      </form>
      {error && <div style={{ color: 'var(--accent)', marginBottom: 12, fontSize: 14 }}>{error}</div>}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', color: '#a1a1aa' }}>
              <th style={{ padding: '10px 0' }}>Member</th>
              <th>Role</th>
              <th>Status</th>
              <th>Joined</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id} style={{ borderTop: '1px solid var(--border)' }}>
                <td style={{ padding: '12px 0' }}>
                  <div style={{ fontWeight: 800, color: '#f4f4f5' }}>{member.name}</div>
                  <div style={{ color: '#a1a1aa', fontSize: 14 }}>{member.email}</div>
                </td>
                <td>{member.role}</td>
                <td>
                  <span style={{
                    padding: '3px 8px',
                    borderRadius: 12,
                    fontSize: 12,
                    fontWeight: 700,
                    background: member.status === 'Active' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                    color: member.status === 'Active' ? '#4ade80' : '#fbbf24',
                    border: member.status === 'Active' ? '1px solid rgba(74, 222, 128, 0.2)' : '1px solid rgba(245, 158, 11, 0.2)'
                  }}>
                    {member.status}
                  </span>
                </td>
                <td>{member.joined || 'Pending'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

