import React, { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/router'

import axios from 'axios'
import GeneratorForm from '../components/GeneratorForm'
import VideoResult from '../components/studio/VideoResult'
import PipelineVisualizer from '../components/PipelineVisualizer'
import ServiceHealth from '../components/ServiceHealth'
import PageShell from '../components/layout/PageShell'
import styles from '../styles/landing.module.css'
import { getAuthToken, getAuthHeader } from '../lib/auth'

export default function Studio() {
  const router = useRouter()
  const [jobId, setJobId] = useState(null)
  const [campaignId, setCampaignId] = useState(null)
  const [status, setStatus] = useState('idle')
  const [videoUrl, setVideoUrl] = useState(null)
  const [error, setError] = useState(null)
  const [initialUrl, setInitialUrl] = useState('')
  const [voiceBackend, setVoiceBackend] = useState('chatterbox')
  const [voiceModel, setVoiceModel] = useState('tts_models/en/ljspeech/tacotron2-DDC')
  const [autoStarted, setAutoStarted] = useState(false)
  const [authReady, setAuthReady] = useState(false)

  const [apiReady, setApiReady] = useState(false)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    const token = getAuthToken()

    if (!token) {
      router.replace('/login')
      return
    }

    setAuthReady(true)
  }, [router])

  useEffect(() => {
    setApiReady(Boolean(API_URL))
  }, [API_URL])

  // Check if URL passed from landing page
  useEffect(() => {
    if (router.query.url) {
      setInitialUrl(router.query.url)
    }
  }, [router.query])

  const handleGenerateAd = useCallback(async (url, userId, options = {}) => {
    setError(null)
    setStatus('generating')

    if (!apiReady) {
      setError('API is not configured.')
      setStatus('error')
      return
    }

    if (typeof window !== 'undefined' && 'Notification' in window) {
      if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
        Notification.requestPermission()
      }
    }
    
    try {
      const response = await axios.post(`${API_URL}/api/ads/generate`, {
        url,
        voice_backend: options.voiceBackend || voiceBackend,
        voice_model: options.voiceModel || voiceModel
      }, { headers: getAuthHeader() })
      
      setJobId(response.data.job_id)
      setCampaignId(response.data.campaign_id)
      setStatus('polling')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start generation')
      setStatus('error')
    }
  }, [API_URL, apiReady, voiceBackend, voiceModel])

  // Auto-trigger generation when URL comes from landing page query param.
  useEffect(() => {
    if (!router.isReady) return
    if (autoStarted) return
    if (!router.query.url || typeof router.query.url !== 'string') return

    const queryUrl = router.query.url.trim()
    if (!queryUrl) return

    setAutoStarted(true)
    handleGenerateAd(queryUrl, 'demo-user', {
      voiceBackend,
      voiceModel,
    })
  }, [router.isReady, router.query.url, autoStarted, handleGenerateAd, voiceBackend, voiceModel])

  const handleJobComplete = (data) => {
    setVideoUrl(data.video_url || data.video_path)
    setStatus('done')

    if (typeof window !== 'undefined' && 'Notification' in window) {
      if (Notification.permission === 'granted') {
        new Notification('Video Generation Complete', {
          body: 'Your AI video ad is ready to view!',
          icon: '/favicon.ico'
        })
      }
    }
  }

  const canGenerate = true

  return (
    authReady ? (
      <PageShell title="Studio" subtitle="Generate high-converting ads in seconds using self-hosted AI models.">
        <div className={styles.studioPremiumWrap} aria-busy={status === 'generating' || status === 'polling'}>
          <div className={styles.studioShell}>
            <section className={styles.studioBoard}>
              <aside className={styles.studioSidebar}>
              <ServiceHealth apiUrl={API_URL} />
              <div className={styles.studioSidebarCard}>
                <div className={styles.onboardTitle}>Generate your ad</div>
                <div className={styles.onboardSub}>Keep the workflow short, visual, and fast</div>
                <div className={styles.studioKpiRow}>
                  <div className={styles.studioKpi}>
                    <span>URL</span>
                    <strong>1 input</strong>
                  </div>
                  <div className={styles.studioKpi}>
                    <span>Flow</span>
                    <strong>6 stages</strong>
                  </div>
                  <div className={styles.studioKpi}>
                    <span>Output</span>
                    <strong>MP4</strong>
                  </div>
                </div>
              </div>

              <div className={styles.studioSidebarCard}>
                <div className={styles.ringLabel}>AI PIPELINE</div>
                <div className={styles.studioPipelineText}>URL → Script → Media → Render</div>
              </div>
            </aside>

            <section className={styles.studioWorkspace}>
              <div className={styles.studioWorkspaceBody}>
                {(status === 'generating' || status === 'polling') && jobId && (
                  <PipelineVisualizer jobId={jobId} url={initialUrl || 'example.com'} apiUrl={API_URL} onComplete={(data) => {
                    const vUrl = data.data?.video_url || data.data?.video_path || data.video_url || data.video_path
                    handleJobComplete({ video_url: vUrl })
                    setStatus('done')
                  }} />
                )}
                {status === 'idle' && (
                  <GeneratorForm
                    onSubmit={handleGenerateAd}
                    initialUrl={initialUrl}
                    voiceBackend={voiceBackend}
                    voiceModel={voiceModel}
                    onVoiceBackendChange={setVoiceBackend}
                    onVoiceModelChange={setVoiceModel}
                    canGenerate={canGenerate}
                  />
                )}

                {status === 'done' && videoUrl && (
                  <VideoResult 
                    videoUrl={videoUrl} 
                    jobId={jobId} 
                    campaignId={campaignId}
                    onNewAd={() => {
                      setStatus('idle')
                      setVideoUrl(null)
                      setJobId(null)
                      setCampaignId(null)
                    }} 
                  />
                )}

                {status === 'error' && error && (
                  <div className={styles.error} role="alert" aria-live="assertive">
                    <h3>Generation error</h3>
                    <p>{error}</p>
                    <button type="button" onClick={() => setStatus('idle')}>Try Again</button>
                  </div>
                )}
              </div>
            </section>
          </section>
        </div>
      </div>
      </PageShell>
    ) : null
  )
}

