import React from 'react'
import { useRouter } from 'next/router'
import styles from '../styles/landing.module.css'

export default function CTABanner() {
  const router = useRouter()
  return (
    <div className={styles.ctaBanner}>
      <div className={styles.ctaTitle}>
        READY TO GENERATE<br/>
        YOUR FIRST <span>AD?</span>
      </div>
      <div className={styles.ctaSub}>
        Paste a URL. Get a TV-ready ad in under 2 minutes. No design skills needed.
      </div>
      <div className={styles.ctaBtns}>
        <button
          onClick={() => router.push('/studio')}
          className={`${styles.btn} ${styles.btnPrimary} ${styles.btnLg}`}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.5">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          Get started free
        </button>
        <button
          onClick={() => router.push('/studio')}
          className={`${styles.btn} ${styles.btnSecondary} ${styles.btnLg}`}
          style={{ borderColor: 'rgba(255,255,255,.25)', color: '#fff' }}
        >
          Book a demo →
        </button>
      </div>
    </div>
  )
}
