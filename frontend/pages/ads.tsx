import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import Link from 'next/link'
import { useRouter } from 'next/router'
import PageShell from '../components/layout/PageShell'
import { getAuthHeader } from '../lib/auth'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function StatusBadge({ status }) {
  const color = status === 'done' ? '#16a34a' : status === 'failed' ? '#dc2626' : status === 'running' ? '#f59e0b' : '#6b7280'
  return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderRadius: 999, background: `${color}18`, color, fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{status || 'queued'}</span>
}

export default function AdsPage() {
  const router = useRouter()
  const [ads, setAds] = useState([])
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')

  useEffect(() => {
    if (typeof window === 'undefined') return
    const token = window.localStorage.getItem('creoad_token')
    if (!token) {
      router.replace('/login')
    }
  }, [router])


  useEffect(() => {
    const load = async () => {
      try {
        const resp = await axios.get(`${API_URL}/api/ads/`, { headers: getAuthHeader() })
        setAds(Array.isArray(resp.data) ? resp.data : [])
      } catch {
        setAds([])
      }
    }
    load()
  }, [])

  const filtered = useMemo(() => ads.filter((item) => {
    const matchesQuery = !query || JSON.stringify(item).toLowerCase().includes(query.toLowerCase())
    const matchesStatus = status === 'all' || (item.status || 'queued') === status
    return matchesQuery && matchesStatus
  }), [ads, query, status])

  return (
    <PageShell title="My Ads" subtitle="Browse generated campaigns, preview output, and open any ad in the editor.">
      <section style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search ads" style={{ minWidth: 280, flex: '1 1 320px', padding: '14px 16px', borderRadius: 14, border: '1px solid var(--border)', background: '#fff' }} />
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ padding: '14px 16px', borderRadius: 14, border: '1px solid var(--border)', background: '#fff' }}>
          <option value="all">All statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="done">Done</option>
          <option value="failed">Failed</option>
        </select>
      </section>

      {filtered.length === 0 ? (
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 20, padding: 28, textAlign: 'center' }}>
          <h3 style={{ margin: 0 }}>No ads yet</h3>
          <p style={{ color: '#555' }}>Generate a campaign in Studio and it will appear here.</p>
          <Link href="/studio" style={{ display: 'inline-flex', marginTop: 8, padding: '12px 16px', borderRadius: 999, background: 'var(--primary)', color: '#fff', textDecoration: 'none', fontWeight: 800 }}>Go to Studio</Link>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 18 }}>
          {filtered.map((ad) => (
            <article key={ad.campaign_id} style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 20, overflow: 'hidden' }}>
              <div style={{ aspectRatio: '16 / 9', background: 'linear-gradient(135deg, #4f46e5, #ff5500)' }} />
              <div style={{ padding: 18 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ margin: '0 0 6px' }}>{ad.business_url || 'Untitled ad'}</h3>
                    <div style={{ color: '#666', fontSize: 14 }}>{ad.video_duration || 30}s · Campaign {ad.campaign_id?.slice(0, 8)}</div>
                  </div>
                  <StatusBadge status={ad.status} />
                </div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 16 }}>
                  <Link href={`/editor?campaign_id=${ad.campaign_id}`} style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--border)', textDecoration: 'none', color: 'var(--text)', fontWeight: 700 }}>Edit</Link>
                  {ad.video_url ? <a href={ad.video_url.startsWith('http') ? ad.video_url : `${API_URL}${ad.video_url}`} download style={{ padding: '10px 12px', borderRadius: 12, border: '1px solid var(--border)', textDecoration: 'none', color: 'var(--text)', fontWeight: 700 }}>Download</a> : null}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </PageShell>
  )
}
