import React, { useEffect, useState } from 'react'
import styles from '../styles/ServiceHealth.module.css'

export default function ServiceHealth({ apiUrl = null }) {
  const [health, setHealth] = useState({})

  useEffect(() => {
    const API = apiUrl || (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
    
    const poll = async () => {
      try {
        const r = await fetch(`${API}/health`)
        if (r.ok) {
          const data = await r.json()
          setHealth(data)
        }
      } catch {
        // network error
      } finally {
      }
    }

    poll()
    const interval = setInterval(poll, 10000)
    return () => clearInterval(interval)
  }, [apiUrl])

  const critical = ['ollama', 'comfyui', 'redis']
  const allOnline = critical.every(s => health[s] === 'online')

  return (
    <div className={styles.panel}>
      <div className={styles.title}>Service Status</div>
      <div className={styles.services}>
        {['ollama', 'comfyui', 'redis', 'postgres', 'minio', 'fastapi'].map(s => (
          <div key={s} className={styles.service}>
            <div className={`${styles.dot} ${health[s] === 'online' ? styles.online : styles.offline}`}></div>
            <span>{s}</span>
          </div>
        ))}
      </div>
      {!allOnline && (
        <div className={styles.warning}>
          {critical.filter(s => health[s] !== 'online').map(s => (
            <div key={s}>{s} offline</div>
          ))}
        </div>
      )}
    </div>
  )
}
