import React from 'react'
import styles from '../styles/landing.module.css'

interface FlowStep {
  num: string
  title: string
  desc: string
  icon: React.ReactNode
  highlight?: 'active' | 'orange'
}

const flowSteps: FlowStep[] = [
  {
    num: '01',
    title: 'Paste URL',
    desc: 'Drop your business URL. CreoAd scrapes brand name, colors, images and messaging instantly.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
      </svg>
    )
  },
  {
    num: '02',
    title: 'AI writes script',
    desc: 'Local LLM (Llama 3.1) generates a 30s scene-by-scene ad script from your scraped brand data.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" strokeWidth="2">
        <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
      </svg>
    ),
    highlight: 'active'
  },
  {
    num: '03',
    title: 'Visuals + voice',
    desc: 'ComfyUI generates scene images. Coqui TTS creates the voiceover. Music added. All local.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff5c00" strokeWidth="2">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <circle cx="8.5" cy="8.5" r="1.5"/>
        <polyline points="21 15 16 10 5 21"/>
      </svg>
    ),
    highlight: 'orange'
  },
  {
    num: '04',
    title: 'Download MP4',
    desc: 'FFmpeg assembles the final ad. Export 16:9 / 9:16 / 1:1. Download and publish anywhere.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
      </svg>
    )
  }
]

export default function HowItWorks() {
  return (
    <section className={`${styles.section} ${styles.howBg}`}>
      <div className={styles.secLabel}>How it works</div>
      <h2 className={styles.secTitle}>
        URL TO AD IN <span>4 STEPS</span>
      </h2>
      <p className={styles.secSub}>
        CreoAd automates the full ad production pipeline using local AI. No human needed.
      </p>

      <div className={styles.stepsFlow}>
        {flowSteps.map((step, idx) => (
          <FlowStepCard key={idx} step={step} />
        ))}
      </div>
    </section>
  )
}

interface FlowStepCardProps {
  step: FlowStep
}

function FlowStepCard({ step }: FlowStepCardProps) {
  const stepClass = step.highlight ? (
    step.highlight === 'active' ? styles.activeStep : styles.orangeStep
  ) : ''

  const iconStyle = step.highlight ? (
    step.highlight === 'active'
      ? { background: 'rgba(79, 70, 229, 0.15)', borderColor: '#4f46e5' }
      : { background: 'rgba(255, 92, 0, 0.15)', borderColor: '#ff5c00' }
  ) : {}

  const titleStyle = step.highlight ? (
    step.highlight === 'active'
      ? { color: '#818cf8' }
      : { color: '#fb923c' }
  ) : {}

  return (
    <div className={`${styles.flowStep} ${stepClass}`}>
      <div className={styles.flowNum}>{step.num}</div>
      <div className={styles.flowIcon} style={iconStyle}>
        {step.icon}
      </div>
      <div className={styles.flowTitle} style={titleStyle}>
        {step.title}
      </div>
      <div className={styles.flowDesc}>
        {step.desc}
      </div>
    </div>
  )
}
