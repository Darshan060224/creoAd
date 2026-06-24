import React, { useState } from 'react'
import { useRouter } from 'next/router'
import styles from '../styles/landing.module.css'

interface Chip {
  label: string
}

const chips: Chip[] = [
  { label: 'Restaurant' },
  { label: 'E-commerce' },
  { label: 'SaaS' },
  { label: 'Real estate' },
  { label: 'Healthcare' },
  { label: 'Automotive' },
  { label: 'Fitness' },
]

export default function Hero() {
  const router = useRouter()
  const [urlInput, setUrlInput] = useState('')

  const handleGenerateClick = () => {
    if (urlInput.trim()) {
      router.push(`/studio?url=${encodeURIComponent(urlInput)}`)
    }
  }

  return (
    <section className={`${styles.gridBg} ${styles.hero}`}>
      <div className={styles.heroInner}>
        <div className={styles.heroCopy}>
          <div className={styles.heroTag}>
            <div className={styles.tagDot}></div>
            Local AI Workflow · Website to Ad Video · Self-Hosted
          </div>

          <h1 className={styles.heroH1}>
            BIG AD.<br/>
            <span className={styles.accent}>ZERO</span> <span className={styles.purple}>COST.</span>
          </h1>

          <p className={styles.heroSub}>
            Turn a company website into a structured ad workflow: scrape, script, visuals, voice, and rendered outputs.
          </p>

          <div className={styles.urlBox}>
            <div className={styles.urlIcon}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#bbb" strokeWidth="2">
                <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
              </svg>
            </div>
            <input
              className={styles.urlInp}
              placeholder="https://yourbusiness.com"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerateClick()}
            />
            <button type="button" className={styles.urlBtn} onClick={handleGenerateClick}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
              Generate Ad
            </button>
          </div>

          <div className={styles.chips}>
            {chips.map((chip, idx) => (
              <div key={idx} className={styles.chip}>{chip.label}</div>
            ))}
          </div>

          <div className={styles.heroRating}>
            <span className={styles.stars}>Workflow</span>
            <span>Input URL → Pipeline stages → Rendered outputs</span>
          </div>
        </div>

        <div className={styles.heroVisual}>
          <Mockup />
        </div>
      </div>
    </section>
  )
}

function Mockup() {
  return (
    <div className={styles.mockupWrap}>
      <div className={styles.mockupOuter}>
        <div className={styles.mockupBar}>
          <div className={styles.dotR}></div>
          <div className={styles.dotY}></div>
          <div className={styles.dotG}></div>
          <div className={styles.mockupUrl}>creoad.io/studio</div>
        </div>

        <div className={styles.mockupBody}>
          <div className={styles.mockNav}>
            <div className={styles.mockLogoT}>
              CREO<span>AD</span>
            </div>
            <div className={styles.mockTabs}>
              <div className={`${styles.mockTab} ${styles.on}`}>Studio</div>
              <div className={styles.mockTab}>My Ads</div>
              <div className={styles.mockTab}>Editor</div>
              <div className={styles.mockTab}>Analytics</div>
            </div>
            <button className={`${styles.btn} ${styles.btnPrimary} ${styles.btnSm}`}
              style={{ fontSize: '10px', padding: '5px 12px' }}>
              + New Ad
            </button>
          </div>

          <div className={styles.mockContent}>
            <div className={styles.mockLeftCol}>
              {/* Stats Row */}
              <div className={styles.mockStatRow}>
                <div className={styles.mockStat}>
                  <div className={styles.mockStatVal}>24</div>
                  <div className={styles.mockStatLbl}>Jobs (sample)</div>
                </div>
                <div className={styles.mockStat}>
                  <div className={styles.mockStatVal} style={{ color: '#4f46e5' }}>6</div>
                  <div className={styles.mockStatLbl}>Running</div>
                </div>
                <div className={styles.mockStat}>
                  <div className={styles.mockStatVal} style={{ color: '#ff5c00' }}>18</div>
                  <div className={styles.mockStatLbl}>Completed</div>
                </div>
              </div>

              {/* Chart */}
              <div className={styles.mockChart}>
                <div className={styles.barC} style={{ height: '30%' }}></div>
                <div className={styles.barC} style={{ height: '50%' }}></div>
                <div className={`${styles.barC} ${styles.accent}`} style={{ height: '40%' }}></div>
                <div className={styles.barC} style={{ height: '70%' }}></div>
                <div className={styles.barC} style={{ height: '55%' }}></div>
                <div className={`${styles.barC} ${styles.accent}`} style={{ height: '80%' }}></div>
                <div className={styles.barC} style={{ height: '65%' }}></div>
                <div className={styles.barC} style={{ height: '90%' }}></div>
                <div className={`${styles.barC} ${styles.accent}`} style={{ height: '75%' }}></div>
                <div className={styles.barC} style={{ height: '100%' }}></div>
              </div>

              {/* Stats Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                <div className={styles.mockStat}>
                  <div style={{ fontSize: '9px', color: '#a1a1aa', marginBottom: '2px' }}>MEDIA STAGES</div>
                  <div className={styles.mockStatVal} style={{ color: '#22c55e' }}>3</div>
                </div>
                <div className={styles.mockStat}>
                  <div style={{ fontSize: '9px', color: '#a1a1aa', marginBottom: '2px' }}>QUEUE STATUS</div>
                  <div className={styles.mockStatVal} style={{ color: '#818cf8' }}>ACTIVE</div>
                </div>
              </div>
            </div>

            {/* Right Panel */}
            <div className={styles.mockRightCol}>
              {/* Video Placeholder */}
              <div className={styles.mockVideoCard}>
                <div style={{ textAlign: 'center' }}>
                  <div className={styles.mockPlayButton}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="#fff">
                      <polygon points="5 3 19 12 5 21 5 3"/>
                    </svg>
                  </div>
                  <div style={{ fontSize: '9px', color: '#a1a1aa', fontFamily: "'Space Mono',monospace" }}>TECHSTORE 30S</div>
                </div>
              </div>

              {/* Progress Card */}
              <div className={styles.mockRightCard}>
                <div style={{ fontSize: '10px', fontWeight: '700', color: '#f4f4f5', marginBottom: '8px', fontFamily: "'Space Mono',monospace" }}>
                  MYBUSINESS.COM
                </div>
                <ProgressRow label="Scraping" percent={100} done />
                <ProgressRow label="Script" percent={100} done />
                <ProgressRow label="Images" percent={70} />
                <ProgressRow label="Voice" percent={0} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

interface ProgressRowProps {
  label: string
  percent: number
  done?: boolean
}

function ProgressRow({ label, percent, done }: ProgressRowProps) {
  const color = done ? '#22c55e' : '#818cf8'
  return (
    <div className={styles.mockProgRow}>
      <span style={{
        width: '5px',
        height: '5px',
        borderRadius: '50%',
        background: color,
        display: 'inline-block'
      }}></span>
      {label}
      <div className={styles.mockProgBar}>
        <div className={styles.mockProgFill} style={{ width: `${percent}%`, background: color }}></div>
      </div>
      <span style={{ color, fontSize: '8px' }}>{done ? '✓' : `${percent}%`}</span>
    </div>
  )
}
