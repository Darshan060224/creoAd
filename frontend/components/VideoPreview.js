import React, { useState } from 'react'
import axios from 'axios'
import styles from '../styles/VideoPreview.module.css'
import EditPanel from './EditPanel'

export default function VideoPreview({ videoUrl, campaignId }) {
  const [editing, setEditing] = useState(false)
  const [campaign, setCampaign] = useState(null)
  const [loading, setLoading] = useState(true)

  const API_URL = process.env.NEXT_PUBLIC_API_URL
  const fullVideoUrl = videoUrl?.startsWith('http') ? videoUrl : (videoUrl ? `${API_URL || 'http://localhost:8000'}${videoUrl}` : '')

  React.useEffect(() => {
    const fetchCampaign = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/campaign/${campaignId}`)
        setCampaign(response.data)
        setLoading(false)
      } catch (err) {
        console.error('Failed to fetch campaign:', err)
        setLoading(false)
      }
    }

    fetchCampaign()
  }, [campaignId, API_URL])

  const handleDownload = () => {
    if (typeof document === 'undefined') return
    const element = document.createElement('a')
    element.href = fullVideoUrl
    element.download = `ad_${campaignId}.mp4`
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  if (loading) {
    return <div className={styles.loading}>Loading campaign data...</div>
  }

  if (editing && campaign) {
    return (
      <EditPanel
        campaign={campaign}
        onClose={() => setEditing(false)}
        onSave={() => setEditing(false)}
      />
    )
  }

  return (
    <div className={styles.preview}>
      <div className={styles.videoContainer}>
          <video
          src={fullVideoUrl}
          controls
          poster={campaign?.scenes?.[0]?.image_url}
          className={styles.video}
            aria-label="Generated ad video preview"
        >
          Your browser does not support the video tag.
        </video>
      </div>

      <div className={styles.info}>
        <h2>Your Ad is Ready! 🎉</h2>
        
        {campaign && (
          <>
            <div className={styles.details}>
              <div className={styles.detailItem}>
                <strong>Business:</strong>
                <span>{campaign.brand_data?.company_name || 'N/A'}</span>
              </div>
              <div className={styles.detailItem}>
                <strong>Duration:</strong>
                <span>{campaign.video_duration}s</span>
              </div>
              <div className={styles.detailItem}>
                <strong>Created:</strong>
                <span>{new Date(campaign.created_at).toLocaleDateString()}</span>
              </div>
            </div>

            {campaign.script && (
              <div className={styles.script}>
                <h3>📝 Ad Script</h3>
                <p className={styles.narration}>{campaign.script.narration}</p>
                <div className={styles.scenes}>
                  {campaign.script.scenes && campaign.script.scenes.map((scene, idx) => (
                    <div key={idx} className={styles.scene}>
                      <strong>Scene {idx + 1}:</strong>
                      <p>{scene.text || scene.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className={styles.actions}>
        <button className={styles.downloadBtn} onClick={handleDownload}>
          ⬇️ Download MP4
        </button>
        <button
          className={styles.editBtn}
          type="button"
          onClick={() => setEditing(true)}
        >
          ✏️ Edit & Re-render
        </button>
        <button
          className={styles.shareBtn}
          type="button"
          onClick={() => window?.alert?.('Share functionality coming soon!')}
        >
          📤 Share
        </button>
      </div>
    </div>
  )
}
