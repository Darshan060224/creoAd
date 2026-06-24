import React, { useState } from 'react'
import { useRouter } from 'next/router'
import styles from '../styles/landing.module.css'

interface NavLink {
  label: string
  id?: string
  active?: boolean
}

const navLinks: NavLink[] = [
  { label: 'Product', active: true },
  { label: 'Features', id: 'features' },
  { label: 'Pricing', id: 'pricing' },
  { label: 'Customers', id: 'testimonials' },
  { label: 'Resources' },
]

export default function Navigation() {
  const router = useRouter()
  const [activeLink, setActiveLink] = useState(0)

  const handleNavClick = (idx: number, sectionId?: string) => {
    setActiveLink(idx)
    if (sectionId) {
      const el = document.getElementById(sectionId)
      el?.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <nav className={styles.nav}>
      <div className={styles.navLogo}>
        <svg width="28" height="28" viewBox="0 0 28 28">
          <rect x="1" y="1" width="11" height="11" rx="3" fill="#4f46e5"/>
          <rect x="15" y="1" width="11" height="11" rx="3" fill="#4f46e5" opacity=".4"/>
          <rect x="1" y="15" width="11" height="11" rx="3" fill="#4f46e5" opacity=".4"/>
          <rect x="15" y="15" width="11" height="11" rx="3" fill="#ff5c00"/>
        </svg>
        <div className={styles.lname}>
          CREO<span>AD</span>
        </div>
      </div>

      <div className={styles.navLinks}>
        {navLinks.map((link, idx) => (
          <div
            key={idx}
            className={`${styles.nl} ${activeLink === idx ? styles.on : ''}`}
            onClick={() => handleNavClick(idx, link.id)}
          >
            {link.label}
          </div>
        ))}
      </div>

      <div className={styles.navRight}>
        <button onClick={() => router.push('/login')} className={`${styles.btn} ${styles.btnSecondary} ${styles.btnSm}`}>
          Log in
        </button>
        <button
          onClick={() => router.push('/login')}
          className={`${styles.btn} ${styles.btnPrimary} ${styles.btnSm}`}
        >
          Get started →
        </button>
      </div>
    </nav>
  )
}
