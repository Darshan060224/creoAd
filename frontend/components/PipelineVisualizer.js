import React, { useEffect, useRef, useState, useCallback } from 'react'
import axios from 'axios'
import styles from '../styles/pipeline.module.css'

// M1 FIX: Map any legacy/unmapped backend stage names to frontend stage IDs
const STAGE_ALIAS = {
  analyzing: 'scrape',
  discovery: 'script',
  vision: 'script',
  strategizing: 'script',
  storyboarding: 'script',
  planning: 'script',
  generating: 'images',
  assembling: 'render',
  done: 'render',
  error: 'render',
}

const WEIGHTS = {
  scrape: 5,
  script: 10,
  images: 50,
  voice: 20,
  music: 5,
  render: 10,
}

function calcOverall(stages) {
  let total = 0
  for (const s of stages) {
    const w = WEIGHTS[s.id] || 0
    if (s.status === 'done') total += w
    else if (s.status === 'active') total += w * (s.pct / 100)
  }
  return Math.round(total)
}

function normalizeStatus(status, pct) {
  if (status === 'success' || status === 'done' || status === 'fallback') return 'done'
  if (status === 'error' || status === 'failed' || status === 'retry_exhausted') return 'error'
  if (status === 'running' || status === 'retrying' || status === 'using_fallback') return 'active'
  if (status === 'active') return 'active'
  if (pct >= 100) return 'done'
  if (pct > 0) return 'active'
  return 'wait'
}

function normalizePct(value, fallback = 0) {
  if (typeof value !== 'number' || Number.isNaN(value)) return fallback
  return Math.min(100, Math.max(0, value))
}

export default function PipelineVisualizer({ jobId, url = 'example.com', apiUrl = null, onComplete = null }) {
  const [modelConfig, setModelConfig] = useState({ ollama_model: 'llama3.2:3b', comfyui_checkpoint: 'sdxl_turbo_fp16.safetensors' })
  const [estimates, setEstimates] = useState({ total: 150 })
  const [selectedImage, setSelectedImage] = useState(null)
  const [stages, setStages] = useState([

    { id: 'scrape', status: 'wait', pct: 0, logs: [], time: null },
    { id: 'script', status: 'wait', pct: 0, logs: [], time: null },
    { id: 'images', status: 'wait', pct: 0, logs: [], time: null, scenes_total: 5, scenes_done: [] },
    { id: 'voice', status: 'wait', pct: 0, logs: [], time: null },
    { id: 'music', status: 'wait', pct: 0, logs: [], time: null },
    { id: 'render', status: 'wait', pct: 0, logs: [], time: null },
  ])

  const [elapsed, setElapsed] = useState(0)
  const elapsedRef = useRef(0)
  const [consoleLines, setConsoleLines] = useState([])
  const consoleRef = useRef(null)
  const wsRef = useRef(null)

  const formatTime = useCallback((value) => {
    const minutes = Math.floor(value / 60)
    const seconds = value % 60
    return `${minutes}:${seconds < 10 ? '0' + seconds : seconds}`
  }, [])

  const stagesRef = useRef(stages)
  useEffect(() => {
    stagesRef.current = stages
  }, [stages])

  useEffect(() => {
    const interval = setInterval(() => {
      const currentStages = stagesRef.current
      const isActive = currentStages.some(s => s.status === 'active')
      const isError = currentStages.some(s => s.status === 'error')
      
      if (isActive && !isError) {
        setElapsed(prev => {
          const next = prev + 1
          elapsedRef.current = next
          return next
        })
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [])

  const appendConsoleLog = useCallback((text, type = 'info') => {
    setConsoleLines(prev => {
      const next = [...prev.slice(-48), { time: formatTime(elapsedRef.current), text, type }]
      setTimeout(() => {
        consoleRef.current?.scrollTo(0, consoleRef.current.scrollHeight)
      }, 50)
      return next
    })
  }, [formatTime])

  const handleMessage = useCallback((data) => {
    if (typeof data.elapsed === 'number') {
      setElapsed(data.elapsed)
      elapsedRef.current = data.elapsed
    }

    if (data.log) appendConsoleLog(data.log)

    const sceneIndex = typeof data.scene_index === 'number' ? data.scene_index : data?.data?.scene_index
    const scenesTotal = typeof data.scenes_total === 'number' ? data.scenes_total : data?.data?.scenes_total
    const pctValue = normalizePct(data.pct, 0)

    if (data.event === 'scene_done' && typeof sceneIndex === 'number') {
      setStages(prev => prev.map(s => {
        if (s.id !== 'images') return s
        const total = scenesTotal || s.scenes_total || 5
        const done = Array.from(new Set([...(s.scenes_done || []), sceneIndex]))
        const pct = pctValue || Math.round((done.length / total) * 100)
        return {
          ...s,
          status: s.status === 'wait' ? 'active' : s.status,
          scenes_total: total,
          scenes_done: done,
          pct,
        }
      }))
    }

    if (data.stage) {
      // M1 FIX: Map backend stage name to frontend stage ID
      const mappedStage = STAGE_ALIAS[data.stage] || data.stage
      setStages(prev => prev.map(s => s.id === mappedStage ? {
        ...s,
        status: normalizeStatus(data.status, pctValue || s.pct),
        pct: pctValue || s.pct,
        logs: data.log ? [...s.logs.slice(-48), data.log] : s.logs,
        time: typeof data.elapsed === 'number' ? data.elapsed : s.time,
      } : s))
    }

    if (data.event === 'pipeline_complete') {
      appendConsoleLog(data.log || 'Pipeline complete', 'ok')
      if (onComplete) onComplete(data)
      if (wsRef.current) wsRef.current.close()
    }

    if (data.event === 'error') {
      appendConsoleLog(data.log || 'Pipeline error', 'error')
      // Mark the reported stage (or current active stage) as error
      setStages(prev => prev.map(s => {
        if (data.stage && s.id === data.stage) return { ...s, status: 'error' }
        if (!data.stage && s.status === 'active') return { ...s, status: 'error' }
        return s
      }))
      if (wsRef.current) wsRef.current.close()
    }
  }, [appendConsoleLog, onComplete])

  useEffect(() => {
    const API = apiUrl || (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
    axios.get(`${API}/health`)
      .then(res => {
        if (res.data?.config) {
          setModelConfig(res.data.config)
        }
      })
      .catch(() => {})
      
    axios.get(`${API}/api/job-metrics/average`)
      .then(res => {
        if (res.data) setEstimates(res.data)
      })
      .catch(() => {})
  }, [apiUrl])

  useEffect(() => {
    if (!jobId) return
    const API = apiUrl || (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
    const wsProto = API.startsWith('https') ? 'wss' : 'ws'
    const token = typeof window !== 'undefined' ? localStorage.getItem('creoad_token') : ''
    const wsUrl = `${wsProto}://${API.replace(/^https?:\/\//, '')}/ws/${jobId}?token=${token}`

    // M7 FIX: Track retry count and limit reconnection attempts
    let retryCount = 0
    const MAX_RETRIES = 10
    let closed = false
    tryConnect()

    function tryConnect() {
      if (retryCount >= MAX_RETRIES) {
        appendConsoleLog(`WebSocket failed after ${MAX_RETRIES} retries — giving up`, 'error')
        return
      }
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        retryCount = 0  // Reset on successful connection
        appendConsoleLog('WebSocket connected')
      }

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          if (data.event === 'pipeline_complete' || data.event === 'error') {
            closed = true
          }
          handleMessage(data)
          if (data.event === 'error' && wsRef.current) {
            wsRef.current.close()
          }
        } catch {
          appendConsoleLog('Invalid WS message')
        }
      }

      ws.onclose = () => {
        if (!closed) {
          retryCount++
          const delay = Math.min(1000 * Math.pow(1.5, retryCount - 1), 10000) // Exponential backoff, max 10s
          appendConsoleLog(`WebSocket disconnected — retry ${retryCount}/${MAX_RETRIES} in ${Math.round(delay / 1000)}s`)
          setTimeout(tryConnect, delay)
        }
      }
    }

    return () => {
      closed = true
      if (wsRef.current) wsRef.current.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, apiUrl])


  // overall progress
  const overall = calcOverall(stages)

  return (
    <div className={styles.visualizerWrap}>
      <div className={styles.header}>
        <div className={styles['header-left']}>
          <h1>CREATING YOUR <span>AD</span></h1>
          <p>{url} · TV 1920×1080 · 30 seconds · {modelConfig.comfyui_checkpoint.replace('.safetensors', '').toUpperCase()} + {modelConfig.ollama_model.toUpperCase()}</p>

        </div>
        <div className={styles['job-info']}>
          <div className={styles['job-badge']}>JOB: {jobId}</div>
        </div>
      </div>

      <div className={styles.grid}>
        <div className={styles.stages}>
          {stages.map(s => (
            <div key={s.id} className={`${styles['stage-card']} ${s.status === 'done' ? styles.done : s.status === 'active' ? styles.active : s.status === 'error' ? styles.error : styles.wait}`}>
              <div className={styles['sc-head']}>
                <div className={styles['sc-icon']}>{s.id === 'scrape' ? '🌐' : s.id === 'script' ? '✍️' : s.id === 'images' ? '🎨' : s.id === 'voice' ? '🎙' : s.id === 'music' ? '🎵' : '🎬'}</div>
                <div className={styles['sc-meta']}>
                  <div className={styles['sc-title']}>{`Stage ${['scrape','script','images','voice','music','render'].indexOf(s.id)+1} — ${s.id.charAt(0).toUpperCase()+s.id.slice(1)}`}</div>
                  <div className={styles['sc-tool']}>{s.id === 'images' ? 'ComfyUI' : s.id === 'script' ? 'Ollama' : s.id === 'voice' ? 'Chatterbox' : ''}</div>
                </div>
                <div className={styles['sc-right']}>
                  <span className={styles.badge + ' ' + (s.status === 'done' ? styles['b-done'] : s.status === 'active' ? styles['b-active'] : s.status === 'error' ? styles['b-error'] : styles['b-wait'])}>
                    {s.status === 'done' ? '✓ Done' : s.status === 'active' ? '⟳ Running' : s.status === 'error' ? '✗ Failed' : 'Queued'}
                  </span>
                  <span className={`${styles['sc-time']} ${s.status === 'done' ? styles['time-done'] : s.status === 'active' ? styles['time-active'] : s.status === 'error' ? styles['time-error'] : styles['time-wait']}`}>{s.time ? `${s.time}s` : s.status === 'done' ? '' : `${s.pct}%`}</span>
                </div>
              </div>
              <div className={styles['sc-body']}>
                <div className={styles['prog-bar-wrap']}><div className={`${styles['prog-bar']} ${s.status === 'done' ? styles['pb-done'] : s.status === 'active' ? styles['pb-active'] : s.status === 'error' ? styles['pb-error'] : styles['pb-wait']}`} style={{ width: `${s.pct}%` }}></div></div>
                {s.id === 'images' && (
                  <div className={styles['scene-grid']}>
                    {Array.from({length: s.scenes_total || 5}).map((_, idx) => {
                      const done = (s.scenes_done || []).includes(idx)
                      const active = !done && s.pct > (idx * 100 / (s.scenes_total || 5)) && s.status === 'active'
                      return (
                        <div 
                          key={idx} 
                          className={`${styles['scene-box']} ${done ? styles['sb-done-bg'] : active ? styles['sb-active-bg'] : styles['sb-wait-bg']}`}
                          style={{ cursor: done ? 'pointer' : 'default' }}
                          onClick={() => {
                            if (done) {
                              const API = apiUrl || (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
                              setSelectedImage(`${API}/output/${jobId}/scene_${String(idx).padStart(2,'0')}.png`)
                            }
                          }}
                        >
                          {done && <div className={styles['scene-check']}>✓</div>}
                          {!done && active && <span className={styles['spin-icon']}>⟳</span>}
                          <span className={styles['scene-label']}>SC {String(idx+1).padStart(2,'0')}</span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className={styles['right-col']}>
          <div className={styles['big-timer']}>
            <div className={styles['timer-label']}>Elapsed time</div>
            <div className={styles['timer-val']}>{Math.floor(elapsed/60)}:{String(elapsed%60).padStart(2,'0')}</div>
            <div className={styles['timer-sub']}>Estimated total: ~{Math.floor(estimates.total/60)} min {Math.round(estimates.total%60)}s</div>
            <div className={styles['timer-pct']}>{overall}% complete</div>
            <div className={styles['overall-bar-wrap']}><div className={styles['overall-bar']} style={{ width: `${overall}%` }}></div></div>
          </div>

          <div className={styles['console-card']}>
            <div className={styles['console-head']}>
              <div className={styles['console-dots']}></div>
              <span className={styles['console-title']}>pipeline.log</span>
            </div>
            <div className={styles['console-body']} ref={consoleRef}>
              {consoleLines.map((l, i) => (
                <div key={i}><span className={styles['cl-time']}>[{l.time}]</span> <span className={styles['cl-ok']}>{l.text}</span></div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {selectedImage && (
        <div
          onClick={() => setSelectedImage(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            cursor: 'zoom-out',
          }}
        >
          <img
            src={selectedImage}
            alt="Generated Scene"
            style={{
              maxWidth: '90vw',
              maxHeight: '90vh',
              borderRadius: 8,
              boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
            }}
          />
        </div>
      )}
    </div>
  )
}
