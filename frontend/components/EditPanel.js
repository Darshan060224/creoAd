import React, { useState } from 'react'
import axios from 'axios'
import styles from '../styles/EditPanel.module.css'
import JobMonitor from './JobMonitor'

export default function EditPanel({ campaign, onClose, onSave }) {
  const [editedText, setEditedText] = useState({})
  const [voiceoverText, setVoiceoverText] = useState(campaign.script?.narration || '')
  const [backgroundMusic, setBackgroundMusic] = useState('upbeat')
  const [voiceBackend, setVoiceBackend] = useState('chatterbox')
  const [voiceModel, setVoiceModel] = useState('tts_models/en/ljspeech/tacotron2-DDC')
  const [rerendering, setRerendering] = useState(false)
  const [rerenderId, setRerenderId] = useState(null)

  const API_URL = process.env.NEXT_PUBLIC_API_URL

  const handleSceneTextChange = (sceneId, newText) => {
    setEditedText({
      ...editedText,
      [sceneId]: newText
    })
  }

  const handleRerender = async () => {
    setRerendering(true)

    try {
      const response = await axios.post(
        `${API_URL}/api/campaign/${campaign.campaign_id}/edit-and-render`,
        {
          scenes: Object.entries(editedText).map(([sceneId, text]) => ({
            scene_id: parseInt(sceneId),
            text
          })),
          voiceover_text: voiceoverText,
          background_music: backgroundMusic,
          voice_backend: voiceBackend,
          voice_model: voiceModel
        }
      )

      setRerenderId(response.data.job_id)
    } catch (err) {
      alert('Failed to start re-render: ' + (err.response?.data?.detail || err.message))
      setRerendering(false)
    }
  }

  if (rerendering && rerenderId) {
    return (
      <JobMonitor
        jobId={rerenderId}
        campaignId={campaign.campaign_id}
        onComplete={() => {
          setRerendering(false)
          onSave()
        }}
        onError={(error) => {
          alert('Re-render failed: ' + error)
          setRerendering(false)
        }}
      />
    )
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2>✏️ Edit Your Ad</h2>
        <button type="button" className={styles.closeBtn} onClick={onClose} aria-label="Close editor">✕</button>
      </div>

      <div className={styles.content}>
        {/* Edit scenes */}
        <section className={styles.section}>
          <h3>Scene Text</h3>
          {campaign.script?.scenes?.map((scene, idx) => (
            <div key={idx} className={styles.sceneEditor}>
              <label>Scene {idx + 1}</label>
              <textarea
                value={editedText[idx] !== undefined ? editedText[idx] : scene.text}
                onChange={(e) => handleSceneTextChange(idx, e.target.value)}
                placeholder={scene.description}
                rows={2}
              />
            </div>
          ))}
        </section>

        {/* Edit voiceover */}
        <section className={styles.section}>
          <h3>Voiceover Text</h3>
          <textarea
            value={voiceoverText}
            onChange={(e) => setVoiceoverText(e.target.value)}
            placeholder="Edit the full narration text"
            rows={4}
          />
        </section>

        {/* Music selection */}
        <section className={styles.section}>
          <h3>Background Music</h3>
          <select value={backgroundMusic} onChange={(e) => setBackgroundMusic(e.target.value)}>
            <option value="upbeat">🎵 Upbeat & Energetic</option>
            <option value="professional">💼 Professional & Corporate</option>
            <option value="calm">😌 Calm & Smooth</option>
            <option value="dramatic">🎬 Dramatic & Bold</option>
            <option value="funky">🎸 Funky & Fun</option>
            <option value="none">❌ No Music</option>
          </select>
        </section>

        <section className={styles.section}>
          <h3>Voice Backend</h3>
          <select value={voiceBackend} onChange={(e) => setVoiceBackend(e.target.value)}>
            <option value="chatterbox">🎙️ Chatterbox Turbo</option>
            <option value="coqui">🎙️ Coqui TTS</option>
            <option value="pyttsx3">🎙️ pyttsx3 fallback</option>
          </select>
          <input
            type="text"
            value={voiceModel}
            onChange={(e) => setVoiceModel(e.target.value)}
            placeholder="Coqui model name"
            aria-label="Coqui model name"
            style={{ marginTop: '0.75rem' }}
          />
        </section>
      </div>

      <div className={styles.actions}>
        <button type="button" className={styles.cancelBtn} onClick={onClose}>Cancel</button>
        <button type="button" className={styles.renderBtn} onClick={handleRerender} disabled={rerendering}>
          {rerendering ? '⏳ Re-rendering...' : '🎬 Re-render Video'}
        </button>
      </div>
    </div>
  )
}
