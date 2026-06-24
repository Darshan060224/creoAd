import React, { useState, useEffect } from 'react'
import styles from '../styles/GeneratorForm.module.css'

export default function GeneratorForm({
  onSubmit,
  initialUrl = '',
  voiceBackend = 'chatterbox',
  voiceModel = 'tts_models/en/ljspeech/tacotron2-DDC',
  onVoiceBackendChange,
  onVoiceModelChange,
  canGenerate = true,
}) {
  const [url, setUrl] = useState(initialUrl)
  const [loading, setLoading] = useState(false)
  const [validationError, setValidationError] = useState('')

  useEffect(() => {
    if (initialUrl) {
      setUrl(initialUrl)
    }
  }, [initialUrl])

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!url.trim()) {
      setValidationError('Please enter a business URL')
      return
    }

    setValidationError('')
    setLoading(true)
    try {
      await onSubmit(url, 'demo-user', {
        voiceBackend,
        voiceModel,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.formGroup}>
        <label htmlFor="url">Business Website URL</label>
        <div className={styles.urlRow}>
          <input
            id="url"
            type="url"
            placeholder="https://example-business.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            autoComplete="url"
            aria-describedby="url-help"
            className={styles.input}
          />
          <button
            type="submit"
            disabled={loading || !canGenerate}
            title={!canGenerate ? 'Critical services offline' : ''}
            className={styles.submitButton}
          >
            {loading ? 'Processing...' : 'Generate Ad'}
          </button>
        </div>
        <p id="url-help" className={styles.helperText}>Enter a publicly accessible website and we’ll generate a campaign from it.</p>
        <div className={styles.info} aria-hidden="false">
          <strong>Examples & Tips</strong>
          <p><strong>Good examples:</strong> product pages, landing pages, or homepages that clearly state the offering and include a hero image and CTA (e.g., https://example.com/product).</p>
          <p><strong>Avoid:</strong> login pages, private/intranet sites, single-image pages, or paywalled content.</p>
          <p><strong>Tip:</strong> if possible, use a page that highlights benefits, features, and a short headline — this helps the scraper produce useful copy and images.</p>
        </div>
        {validationError && <div className={styles.validationError} role="alert">{validationError}</div>}
      </div>

      <div className={styles.quickInfo}>
        <p>URL in, ad out. The pipeline stays short and visual.</p>
        <p>Scrape, script, media, and render run as one flow.</p>
      </div>

      <div className={styles.formGroup}>
        <label htmlFor="voiceBackend">Voice backend</label>
        <select
          id="voiceBackend"
          value={voiceBackend}
          onChange={(e) => onVoiceBackendChange?.(e.target.value)}
          aria-label="Select voice backend"
          className={styles.input}
        >
          <option value="chatterbox">Chatterbox Turbo</option>
          <option value="coqui">Coqui TTS</option>
          <option value="pyttsx3">pyttsx3 fallback</option>
        </select>
      </div>

      <div className={styles.formGroup}>
        <label htmlFor="voiceModel">Coqui model</label>
        <input
          id="voiceModel"
          type="text"
          placeholder="tts_models/en/ljspeech/tacotron2-DDC"
          value={voiceModel}
          onChange={(e) => onVoiceModelChange?.(e.target.value)}
          aria-label="Coqui model name"
          className={styles.input}
        />
      </div>
    </form>
  )
}
