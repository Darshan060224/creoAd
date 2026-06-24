import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import axios from 'axios'
import PageShell from '../components/layout/PageShell'
import VideoPreview from '../components/VideoPreview'
import { getAuthHeader } from '../lib/auth'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function EditorPage() {
  const router = useRouter()
  const [campaignId, setCampaignId] = useState(null)
  const [campaign, setCampaign] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const token = window.localStorage.getItem('creoad_token')
    if (!token) {
      router.replace('/login')
    }
  }, [router])

  useEffect(() => {
    if (!router.isReady) return
    const id = router.query.campaign_id
    if (id) {
      setCampaignId(id)
    } else {
      setLoading(false)
    }
  }, [router.isReady, router.query])

  useEffect(() => {
    if (!campaignId) return
    const loadCampaign = async () => {
      try {
        const resp = await axios.get(`${API_URL}/api/campaign/${campaignId}`, { headers: getAuthHeader() })
        setCampaign(resp.data)
      } catch (err) {
        console.error('Failed to load campaign', err)
      } finally {
        setLoading(false)
      }
    }
    loadCampaign()
  }, [campaignId])

  return (
    <PageShell title="Editor" subtitle="Review script, preview the ad, and refine the output.">
      {loading ? (
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 20, padding: 30, textAlign: 'center' }}>
          Loading campaign editor...
        </div>
      ) : campaignId && campaign ? (
        <div style={{ maxWidth: 840, margin: '0 auto' }}>
          <VideoPreview videoUrl={campaign.video_url} campaignId={campaignId} />
        </div>
      ) : (
        <div style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 20, padding: 30, textAlign: 'center' }}>
          <h3 style={{ margin: 0 }}>No campaign selected</h3>
          <p style={{ color: '#555', marginTop: 8 }}>Please select a campaign from your list of ads to edit.</p>
          <button
            onClick={() => router.push('/ads')}
            style={{
              marginTop: 16,
              padding: '12px 24px',
              borderRadius: 999,
              background: 'var(--purple)',
              color: '#fff',
              border: 'none',
              fontWeight: 800,
              cursor: 'pointer'
            }}
          >
            Go to My Ads
          </button>
        </div>
      )}
    </PageShell>
  )
}

