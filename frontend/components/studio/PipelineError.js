import React, { useState } from 'react'

/**
 * PipelineError — shown when a pipeline stage fails.
 * Shows the error details plus a Retry button that re-enqueues
 * the job using the checkpoint system.
 */
export default function PipelineError({ jobId, campaignId, failedStage, errorMessage, onRetry, apiUrl }) {
  const [retrying, setRetrying] = useState(false)
  const [retryResult, setRetryResult] = useState(null)
  const API = apiUrl || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const handleRetry = async () => {
    setRetrying(true)
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('creoad_token') : ''
      const res = await fetch(`${API}/api/ads/${campaignId}/retry`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      const data = await res.json()
      setRetryResult(data)
      if (onRetry) onRetry(data)
    } catch (err) {
      setRetryResult({ error: err.message })
    } finally {
      setRetrying(false)
    }
  }

  return (
    <div
      style={{
        background: '#fff8f5',
        border: '1.5px solid #ef4444',
        borderRadius: 12,
        padding: 20,
        marginTop: 16,
        boxShadow: '3px 3px 0 #fca5a5',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <div
          style={{
            width: 28,
            height: 28,
            background: '#fee2e2',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 14,
          }}
        >
          ✗
        </div>
        <div style={{ fontWeight: 700, color: '#ef4444', fontSize: 14, fontFamily: 'DM Mono, monospace' }}>
          FAILED AT: {(failedStage || 'render').toUpperCase()}
        </div>
      </div>

      {errorMessage && (
        <div
          style={{
            fontSize: 11,
            color: '#888',
            marginBottom: 14,
            fontFamily: 'DM Mono, monospace',
            background: '#fef2f2',
            padding: '8px 12px',
            borderRadius: 6,
            maxHeight: 100,
            overflow: 'auto',
            wordBreak: 'break-all',
          }}
        >
          {errorMessage.length > 200 ? errorMessage.slice(-200) : errorMessage}
        </div>
      )}

      <div
        style={{
          fontSize: 12,
          color: '#16a34a',
          marginBottom: 14,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <span>✓</span>
        <span>Earlier stages saved — retry will skip completed work and resume from &ldquo;{failedStage || 'render'}&rdquo;</span>
      </div>

      {retryResult && retryResult.job_id && (
        <div
          style={{
            fontSize: 11,
            color: '#4f46e5',
            marginBottom: 10,
            fontFamily: 'DM Mono, monospace',
          }}
        >
          ↻ Re-queued as job {retryResult.job_id.slice(0, 8)}...
        </div>
      )}

      {retryResult && retryResult.error && (
        <div style={{ fontSize: 11, color: '#ef4444', marginBottom: 10 }}>
          Retry failed: {retryResult.error}
        </div>
      )}

      <button
        onClick={handleRetry}
        disabled={retrying || (retryResult && retryResult.job_id)}
        style={{
          background: retrying ? '#666' : '#0a0a0a',
          color: '#fff',
          border: 'none',
          borderRadius: 8,
          padding: '10px 20px',
          fontWeight: 700,
          fontSize: 13,
          cursor: retrying ? 'wait' : 'pointer',
          fontFamily: 'DM Sans, sans-serif',
          opacity: retryResult && retryResult.job_id ? 0.5 : 1,
        }}
      >
        {retrying ? '⟳ Retrying...' : `↻ Resume from ${failedStage || 'render'}`}
      </button>
    </div>
  )
}
