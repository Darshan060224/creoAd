import React from 'react'
import styles from '../styles/landing.module.css'

interface Logo {
  name: string
}

const logos: Logo[] = [
  { name: 'FANATICS' },
  { name: 'BUMBLE' },
  { name: 'MOOD' },
  { name: 'TERRA KAFFE' },
  { name: 'BATCH' },
  { name: 'PETFOLK' },
  { name: 'SIJO' },
]

export default function LogoTrust() {
  return (
    <div className={styles.logosSection}>
      <div className={styles.logosLabel}>Trusted by 10,000+ businesses</div>
      <div className={styles.logosRow}>
        {logos.map((logo, idx) => (
          <div key={idx} className={styles.logoPill}>{logo.name}</div>
        ))}
      </div>
    </div>
  )
}
