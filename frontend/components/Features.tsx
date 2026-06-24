import React from 'react'
import styles from '../styles/landing.module.css'

interface Feature {
  title: string
  desc: string
  icon: React.ReactNode
  color?: string
}

const features: Feature[] = [
  {
    title: 'URL to Ad in 2 mins',
    desc: 'Paste any URL and get a complete TV-ready video ad — script, visuals, voiceover, music — fully automated.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="2" y1="12" x2="22" y2="12"/>
        <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/>
      </svg>
    )
  },
  {
    title: '100% Local AI',
    desc: 'Ollama, ComfyUI, Coqui TTS run on your machine. Zero per-generation cost. Full data privacy.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff5c00" strokeWidth="2">
        <rect x="2" y="3" width="20" height="14" rx="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/>
        <line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
    ),
    color: '#ff5c00'
  },
  {
    title: 'Powerful editor',
    desc: 'Edit script, swap voice, regenerate individual scenes without rerunning the full pipeline.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" strokeWidth="2">
        <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/>
      </svg>
    )
  },
  {
    title: 'Live progress',
    desc: 'Watch each stage in real time — scraping, script, images, voice, assembly. Redis async pipeline.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff5c00" strokeWidth="2">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
    ),
    color: '#ff5c00'
  },
  {
    title: 'Multi-format export',
    desc: '16:9 TV, 9:16 vertical, 1:1 square. H.264 MP4 ready to publish on any platform.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" strokeWidth="2">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
      </svg>
    )
  },
  {
    title: 'Oracle Cloud native',
    desc: 'Deploys on OCI GPU instances. Docker + Nginx ready. Scales to enterprise workloads.',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff5c00" strokeWidth="2">
        <rect x="2" y="2" width="20" height="8" rx="2"/>
        <rect x="2" y="14" width="20" height="8" rx="2"/>
        <line x1="6" y1="6" x2="6.01" y2="6"/>
        <line x1="6" y1="18" x2="6.01" y2="18"/>
      </svg>
    ),
    color: '#ff5c00'
  }
]

export default function Features() {
  return (
    <section className={`${styles.section} ${styles.gridBg}`}>
      <div className={styles.secLabel}>Features</div>
      <h2 className={styles.secTitle}>
        EVERYTHING YOU NEED<br/>
        TO <span>CREATE GREAT ADS</span>
      </h2>
      <p className={styles.secSub}>
        Built for performance marketers and agencies. No design skills needed.
      </p>

      <div className={styles.featGrid}>
        {features.map((feature, idx) => (
          <FeatureCard key={idx} feature={feature} />
        ))}
      </div>
    </section>
  )
}

interface FeatureCardProps {
  feature: Feature
}

function FeatureCard({ feature }: FeatureCardProps) {
  const iconBorder = feature.color === '#ff5c00' ? '#ff5c00' : '#0a0a0a'

  return (
    <div className={styles.featCard}>
      <div className={styles.featIcon} style={{ borderColor: iconBorder }}>
        {feature.icon}
      </div>
      <div className={styles.featTitle}>
        {feature.title}
      </div>
      <div className={styles.featDesc}>
        {feature.desc}
      </div>
    </div>
  )
}
