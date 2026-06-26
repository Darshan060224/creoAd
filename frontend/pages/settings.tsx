import React, { useEffect, useState } from 'react'
import axios from 'axios'
import PageShell from '../components/layout/PageShell'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function SettingsPage() {
  const [health, setHealth] = useState({})

  useEffect(() => {
    if (typeof window === 'undefined') return
    const token = window.localStorage.getItem('creoad_token')
    if (!token) window.location.href = '/login'
  }, [])

  useEffect(() => {
    axios.get(`${API_URL}/health`).then((resp) => setHealth(resp.data)).catch(() => setHealth({}))
  }, [])

  const services = ['ollama', 'comfyui', 'redis', 'postgres', 'minio', 'fastapi']

  return (
    <PageShell title="Settings" subtitle="Tune models, outputs, and infrastructure health.">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
        <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 20, padding: 20 }}>
          <h3 style={{ marginTop: 0 }}>Model selectors</h3>
          <label>Ollama model</label>
          <select style={{ width: '100%', margin: '8px 0 14px', padding: 12, borderRadius: 12, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }}><option>llama3.2:3b</option><option>mistral:7b</option></select>
          <label>TTS backend</label>
          <select style={{ width: '100%', margin: '8px 0 14px', padding: 12, borderRadius: 12, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }}><option>Chatterbox</option><option>Coqui</option></select>
          <label>FFmpeg preset</label>
          <select style={{ width: '100%', marginTop: 8, padding: 12, borderRadius: 12, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }}><option>ultrafast</option><option>veryfast</option><option>fast</option></select>
        </section>
        <section style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 20, padding: 20 }}>
          <h3 style={{ marginTop: 0 }}>Service health</h3>
          <div style={{ display: 'grid', gap: 12 }}>
            {services.map((service) => (
              <div key={service} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 14px', border: '1px solid var(--border)', borderRadius: 14 }}>
                <span style={{ textTransform: 'capitalize', fontWeight: 700 }}>{service}</span>
                <span style={{ fontWeight: 800, color: health?.[service] === 'online' || health?.[service]?.status === 'online' ? '#16a34a' : '#dc2626' }}>{health?.[service] === 'online' || health?.[service]?.status === 'online' ? 'online' : 'offline'}</span>
              </div>
            ))}
          </div>
        </section>
      </div>
    </PageShell>
  )
}
