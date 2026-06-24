import React from 'react'
import styles from '../styles/landing.module.css'

interface FooterLink {
  label: string
}

interface FooterColumn {
  title: string
  links: FooterLink[]
}

const footerColumns: FooterColumn[] = [
  {
    title: 'Product',
    links: [
      { label: 'Studio' },
      { label: 'Features' },
      { label: 'Pricing' },
      { label: 'Changelog' },
      { label: 'Roadmap' }
    ]
  },
  {
    title: 'Resources',
    links: [
      { label: 'Docs' },
      { label: 'API' },
      { label: 'Blog' },
      { label: 'Help center' },
      { label: 'Status' }
    ]
  },
  {
    title: 'Company',
    links: [
      { label: 'About' },
      { label: 'Customers' },
      { label: 'Careers' },
      { label: 'Contact' }
    ]
  },
  {
    title: 'Legal',
    links: [
      { label: 'Privacy' },
      { label: 'Terms' },
      { label: 'Security' },
      { label: 'Cookies' }
    ]
  }
]

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerTop}>
        <div className={styles.footerBrand}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <svg width="24" height="24" viewBox="0 0 28 28">
              <rect x="1" y="1" width="11" height="11" rx="3" fill="#4f46e5"/>
              <rect x="15" y="1" width="11" height="11" rx="3" fill="#4f46e5" opacity=".4"/>
              <rect x="1" y="15" width="11" height="11" rx="3" fill="#4f46e5" opacity=".4"/>
              <rect x="15" y="15" width="11" height="11" rx="3" fill="#ff5c00"/>
            </svg>
            <div className={styles.footerBrandName}>
              CREO<span>AD</span>
            </div>
          </div>
          <p>
            AI-powered ad creation. 100% local. Oracle Cloud ready. Zero per-generation cost.
          </p>
          <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
            <div className={styles.socialIcon}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2">
                <path d="M23 3a10.9 10.9 0 01-3.14 1.53 4.48 4.48 0 00-7.86 3v1A10.66 10.66 0 013 4s-4 9 5 13a11.64 11.64 0 01-7 2c9 5 20 0 20-11.5a4.5 4.5 0 00-.08-.83A7.72 7.72 0 0023 3z"/>
              </svg>
            </div>
            <div className={styles.socialIcon}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2">
                <path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z"/>
                <circle cx="4" cy="4" r="2"/>
              </svg>
            </div>
            <div className={styles.socialIcon}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#555" strokeWidth="2">
                <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 00-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0020 4.77 5.07 5.07 0 0019.91 1S18.73.65 16 2.48a13.38 13.38 0 00-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 005 4.77a5.44 5.44 0 00-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 009 18.13V22"/>
              </svg>
            </div>
          </div>
        </div>

        {footerColumns.map((column, idx) => (
          <div key={idx}>
            <div className={styles.footerColTitle}>
              {column.title}
            </div>
            <div className={styles.footerLinks}>
              {column.links.map((link, linkIdx) => (
                <div key={linkIdx} className={styles.footerLink}>
                  {link.label}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className={styles.footerBottom}>
        <div className={styles.footerCopy}>
          © 2026 CreoAd. All rights reserved.
        </div>
        <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: '#888' }}>
          <span>Privacy</span>
          <span>·</span>
          <span>Terms</span>
          <span>·</span>
          <span>Cookies</span>
        </div>
      </div>
    </footer>
  )
}
