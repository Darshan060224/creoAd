import React, { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import styles from '../styles/JobMonitor.module.css'

const STAGE_NAMES = {
  scrape: '📄 Scraping Content',
  script: '✍️ Generating Script',
  media: '🎛️ Creating Images + Voice + Music',
  video: '🎬 Assembling Video',
  storage: '🗂️ Uploading to MinIO',
  db: '🧾 Saving Job Record'
}

export default function JobMonitor({ jobId, campaignId, onComplete, onError }) {
  const [progress, setProgress] = useState({})
  const [logs, setLogs] = useState([])
  const [stage, setStage] = useState('scrape')
  const [completed, setCompleted] = useState(false)
  const [elapsed, setElapsed] = useState(0)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const pollStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${API_URL}/api/job-status/${jobId}`)
      const data = response.data

      setProgress(data.progress || {})
      setLogs(Array.isArray(data.logs) ? data.logs : [])
      const currentStage = data.progress?.stage || 'scrape'
      setStage(currentStage)

      if (data.status === 'finished' || data.status === 'complete') {
        setCompleted(true)
        // Fetch final campaign data
        const campaignResponse = await axios.get(`${API_URL}/api/campaign/${campaignId}`)
        onComplete(campaignResponse.data)
      } else if (data.status === 'failed') {
        onError(data.error || 'Job failed')
      }
    } catch (err) {
      console.error('Poll error:', err)
      // Continue polling even if there's an error
    }
  }, [API_URL, jobId, campaignId, onComplete, onError])

  useEffect(() => {
    let intervalId

    // Poll immediately, then every 2 seconds
    pollStatus()
    intervalId = setInterval(pollStatus, 2000)

    return () => clearInterval(intervalId)
  }, [pollStatus])

  // Track elapsed time
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(e => e + 1)
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  const stagePath = ['scrape', 'script', 'media', 'video', 'storage', 'db']
  const currentStageIndex = stagePath.indexOf(stage)
  const stageMessages = logs.slice(-6)

  return (
    <div className={styles.monitor} role="status" aria-live="polite">
      <div className={styles.header}>
        <h2>🔄 Creating Your Ad...</h2>
        <p className={styles.elapsed}>{Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, '0')}</p>
      </div>

      {/* Progress bar */}
      <div className={styles.progressContainer}>
        {stagePath.map((s, idx) => (
          <div
            key={s}
            className={`${styles.progressStage} ${
              idx <= currentStageIndex ? styles.active : ''
            } ${idx === currentStageIndex && !completed ? styles.current : ''}`}
            title={STAGE_NAMES[s]}
            aria-label={STAGE_NAMES[s]}
          >
            <span>{s.charAt(0).toUpperCase()}</span>
          </div>
        ))}
      </div>

      {/* Current stage */}
      <div className={styles.currentStage}>
        <h3>{STAGE_NAMES[stage]}</h3>
        <p className={styles.message}>{progress.message || 'Processing...'}</p>
      </div>

      {stageMessages.length > 0 && (
        <div className={styles.timeline}>
          {stageMessages.map((log, idx) => (
            <div key={`${log.stage}-${idx}`} className={styles.timelineItem}>
              <div className={styles.timelineDot + ' ' + styles[log.status]} />
              <div className={styles.timelineBody}>
                <div className={styles.timelineTitle}>{STAGE_NAMES[log.stage] || log.stage}</div>
                <div className={styles.timelineMessage}>{log.message}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Animation */}
      <div className={styles.animation}>
        <div className={styles.spinner}></div>
      </div>

      {completed && (
        <div className={styles.complete}>
          <p>✅ Ad generation complete!</p>
        </div>
      )}
    </div>
  )
}
