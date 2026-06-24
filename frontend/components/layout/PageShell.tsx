import React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
import Head from 'next/head'

const navItems = [
  { href: '/studio', label: 'Studio' },
  { href: '/ads', label: 'My Ads' },
  { href: '/editor', label: 'Editor' },
  { href: '/analytics', label: 'Analytics' },
  { href: '/team', label: 'Team' },
  { href: '/settings', label: 'Settings' },
]

export default function PageShell({ title, subtitle, children, rightRail = null }) {
  const router = useRouter()
  const currentPath = router.pathname

  const bg = '#09090b'
  const text = '#f4f4f5'
  const headerBg = 'rgba(9, 9, 11, 0.8)'
  const headerBorder = 'rgba(255, 255, 255, 0.08)'
  const subtitleColor = '#a1a1aa'

  return (
    <div style={{ minHeight: '100vh', background: bg, color: text }}>
      <Head>
        <title>{title ? `${title} | CreoAd` : 'CreoAd'}</title>
      </Head>
      <header style={{ position: 'sticky', top: 0, zIndex: 100, background: headerBg, backdropFilter: 'blur(10px)', borderBottom: `1px solid ${headerBorder}` }}>
        <div style={{ maxWidth: 1440, margin: '0 auto', padding: '16px 24px', display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent)' }}>CreoAd</div>
            <div style={{ fontSize: 22, fontWeight: 800 }}>{title}</div>
            {subtitle ? <div style={{ color: subtitleColor, marginTop: 4 }}>{subtitle}</div> : null}
          </div>
          <nav style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {navItems.map((item) => {
              const isActive = currentPath === item.href || (item.href !== '/studio' && currentPath.startsWith(item.href))
              
              const itemBg = isActive ? 'var(--purple)' : 'rgba(255,255,255,0.05)'
              const itemColor = isActive ? '#fff' : '#d4d4d8'
              const itemBorder = isActive ? 'var(--purple)' : 'rgba(255,255,255,0.1)'

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  style={{
                    padding: '10px 18px',
                    borderRadius: 999,
                    border: `1.5px solid ${itemBorder}`,
                    background: itemBg,
                    textDecoration: 'none',
                    color: itemColor,
                    fontWeight: 700,
                    fontSize: 14,
                    transition: 'all 0.2s ease',
                    boxShadow: isActive ? '0 2px 8px rgba(79, 70, 229, 0.25)' : 'none'
                  }}
                >
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>
      </header>

      <main style={{ maxWidth: 1440, margin: '0 auto', padding: 0 }}>
        <div style={{ display: 'grid', gridTemplateColumns: rightRail ? 'minmax(0, 1fr) 320px' : '1fr', gap: 0, alignItems: 'start' }}>
          <div style={{ width: '100%' }}>{children}</div>
          {rightRail ? <aside>{rightRail}</aside> : null}
        </div>
      </main>
    </div>
  )
}