import React, { useEffect, useState, useMemo } from 'react'
import axios from 'axios'
import PageShell from '../components/layout/PageShell'
import { getAuthHeader } from '../lib/auth'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function AnalyticsPage() {
  const [ads, setAds] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const token = window.localStorage.getItem('creoad_token')
    if (!token) {
      window.location.href = '/login'
      return
    }

    const loadData = async () => {
      try {
        const resp = await axios.get(`${API_URL}/api/ads/`, { headers: getAuthHeader() })
        setAds(Array.isArray(resp.data) ? resp.data : [])
      } catch (err) {
        console.error('Failed to load analytics data', err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  // Calculate metrics
  const stats = useMemo(() => {
    const total = ads.length
    const completed = ads.filter(ad => ad.status === 'done')
    const failed = ads.filter(ad => ad.status === 'failed' || ad.status === 'error')
    
    // Avg duration
    let avgTimeStr = 'N/A'
    if (completed.length > 0) {
      const totalMs = completed.reduce((sum, ad) => {
        if (!ad.created_at || !ad.updated_at) return sum
        const diff = new Date(ad.updated_at).getTime() - new Date(ad.created_at).getTime()
        return sum + (diff > 0 ? diff : 0)
      }, 0)
      const avgSecs = Math.round((totalMs / completed.length) / 100) / 10
      const mins = Math.floor(avgSecs / 60)
      const secs = Math.round(avgSecs % 60)
      avgTimeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
    }

    // Success rate
    const totalClosed = completed.length + failed.length
    const rate = totalClosed > 0 ? Math.round((completed.length / totalClosed) * 100) : 100

    // Exports
    const exportsCount = completed.filter(ad => ad.video_url).length

    return [
      { label: 'Total ads', value: String(total) },
      { label: 'Avg generation time', value: avgTimeStr },
      { label: 'Success rate', value: `${rate}%` },
      { label: 'Exports', value: String(exportsCount) },
    ]
  }, [ads])

  // Get data for last 7 days chart
  const chartData = useMemo(() => {
    const days = []
    for (let i = 6; i >= 0; i--) {
      const d = new Date()
      d.setDate(d.getDate() - i)
      days.push({
        dateStr: d.toISOString().split('T')[0],
        label: d.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })
      })
    }

    const counts = days.map(day => {
      return ads.filter(ad => ad.created_at && ad.created_at.startsWith(day.dateStr)).length
    })

    const maxVal = Math.max(...counts, 4) // minimum scale of 4
    
    // Map to SVG coordinates: X from 40 to 560, Y from 180 (val=0) to 40 (val=maxVal)
    const points = days.map((_, idx) => {
      const x = 50 + idx * 80
      const y = 180 - (counts[idx] / maxVal) * 130
      return { x, y, count: counts[idx], label: days[idx].label }
    })

    const polylinePoints = points.map(p => `${p.x},${p.y}`).join(' ')

    return { points, polylinePoints, maxVal }
  }, [ads])

  return (
    <PageShell title="Analytics" subtitle="See campaign throughput, reliability, and recent activity.">
      {loading ? (
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 20, padding: 40, textAlign: 'center' }}>
          Loading analytics metrics...
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 20 }}>
            {stats.map((item) => (
              <div key={item.label} style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 18, padding: 18 }}>
                <div style={{ color: '#666', fontSize: 13 }}>{item.label}</div>
                <div style={{ fontSize: 28, fontWeight: 900, marginTop: 6 }}>{item.value}</div>
              </div>
            ))}
          </div>

          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 20, padding: 20, marginBottom: 20 }}>
            <h3 style={{ marginTop: 0, marginBottom: 20 }}>Ads per day (Last 7 Days)</h3>
            <div style={{ position: 'relative', height: 220 }}>
              <svg viewBox="0 0 600 220" width="100%" height="220" role="img" aria-label="Ads per day chart">
                {/* Grid Lines */}
                <line x1="40" y1="50" x2="560" y2="50" stroke="#f0f0ee" strokeWidth="1" />
                <line x1="40" y1="115" x2="560" y2="115" stroke="#f0f0ee" strokeWidth="1" />
                <line x1="40" y1="180" x2="560" y2="180" stroke="#e0e0dc" strokeWidth="1.5" />

                {/* Line graph */}
                {chartData.points.length > 0 && (
                  <>
                    <polyline fill="none" stroke="var(--purple)" strokeWidth="3.5" points={chartData.polylinePoints} strokeLinecap="round" strokeLinejoin="round" />
                    <g fill="var(--accent)">
                      {chartData.points.map((p, idx) => (
                        <g key={idx}>
                          <circle cx={p.x} cy={p.y} r="5.5" style={{ transition: 'all 0.3s ease' }} />
                          {/* Tooltip/Count label above dot */}
                          <text x={p.x} y={p.y - 12} textAnchor="middle" fontSize="11" fontWeight="800" fill="var(--text)">
                            {p.count > 0 ? p.count : ''}
                          </text>
                          {/* Date label at bottom */}
                          <text x={p.x} y="200" textAnchor="middle" fontSize="11" fontWeight="700" fill="#666">
                            {p.label}
                          </text>
                        </g>
                      ))}
                    </g>
                  </>
                )}
              </svg>
            </div>
          </div>

          <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 20, padding: 20 }}>
            <h3 style={{ marginTop: 0, marginBottom: 15 }}>Recent jobs</h3>
            {ads.length === 0 ? (
              <div style={{ padding: '20px 0', color: '#666', textAlign: 'center' }}>No campaigns found.</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ textAlign: 'left', color: '#555', fontSize: 13, borderBottom: '1.5px solid var(--border)' }}>
                      <th style={{ padding: '10px 8px' }}>Campaign / URL</th>
                      <th style={{ padding: '10px 8px' }}>Created</th>
                      <th style={{ padding: '10px 8px' }}>Duration</th>
                      <th style={{ padding: '10px 8px' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ads.slice(0, 10).map((ad) => {
                      let durationStr = 'N/A'
                      if (ad.created_at && ad.updated_at && ad.status === 'done') {
                        const diffSecs = Math.round((new Date(ad.updated_at).getTime() - new Date(ad.created_at).getTime()) / 1000)
                        const mins = Math.floor(diffSecs / 60)
                        const secs = diffSecs % 60
                        durationStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
                      } else if (ad.status !== 'done' && ad.status !== 'failed' && ad.status !== 'error') {
                        durationStr = 'Running...'
                      }
                      
                      const isComplete = ad.status === 'done'
                      const isErr = ad.status === 'failed' || ad.status === 'error'

                      return (
                        <tr key={ad.campaign_id} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ padding: '14px 8px', fontWeight: 700 }}>
                            <div style={{ fontSize: 14 }}>{ad.business_url}</div>
                            <div style={{ fontSize: 11, color: '#888', marginTop: 2, fontFamily: 'DM Mono, monospace' }}>ID: {ad.campaign_id}</div>
                          </td>
                          <td style={{ padding: '14px 8px', fontSize: 13, color: '#555' }}>
                            {ad.created_at ? new Date(ad.created_at).toLocaleString() : 'N/A'}
                          </td>
                          <td style={{ padding: '14px 8px', fontSize: 13, color: '#555' }}>
                            {durationStr}
                          </td>
                          <td style={{ padding: '14px 8px' }}>
                            <span style={{
                              padding: '4px 10px',
                              borderRadius: 12,
                              fontSize: 11,
                              fontWeight: 800,
                              textTransform: 'uppercase',
                              background: isComplete ? '#dcfce7' : isErr ? '#fee2e2' : '#fef3c7',
                              color: isComplete ? '#16a34a' : isErr ? '#dc2626' : '#d97706'
                            }}>
                              {ad.status}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </PageShell>
  )
}

