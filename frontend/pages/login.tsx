import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import axios from 'axios'
import styles from '../styles/landing.module.css'
import { getAuthToken, setAuthSession } from '../lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (getAuthToken()) {
      router.replace('/studio')
    }
  }, [router])

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError('')

    try {
      const endpoint = mode === 'login' ? '/api/users/login' : '/api/users/register'
      const payload = mode === 'login'
        ? { email, password }
        : { full_name: fullName, email, password }

      const response = await axios.post(API_URL + endpoint, payload)
      setAuthSession(response.data.access_token, response.data.user)
      router.replace('/studio')
    } catch (error: unknown) {
      if (axios.isAxiosError(error)) {
        setError(error.response?.data?.detail || 'Authentication failed')
      } else if (error instanceof Error) {
        setError(error.message)
      } else {
        setError('Authentication failed')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.gridBg + ' ' + styles.authPage}>
      <main className={styles.authPageInner}>
        <section className={styles.authShell}>

          <div className={styles.authHeader}>
            <div className={styles.authTag}>
              <span className={styles.authTagDot} />
              Secure access · Self-hosted AI workflow
            </div>

            <div className={styles.authTitleWrap}>
              <h1 className={styles.authTitle}>
                LOG IN <span className={styles.authTitleLine}>
                  <span className={styles.authAccentOrange}>TO</span>{' '}
                  <span className={styles.authAccentBlue}>CREOAD.</span>
                </span>
              </h1>

              <p className={styles.heroSub}>
                Access your studio, generate ads, and manage AI campaigns securely.
              </p>

              <div className={styles.authPreviewBottom}>
                <div className={styles.featureCard}>
                  <div className={styles.featureIconBlue}>S</div>
                  <div>
                    <div className={styles.featureTitle}>Secure local authentication</div>
                    <div className={styles.featureDesc}>Self-hosted SQLite auth with JWT sessions.</div>
                  </div>
                </div>

                <div className={styles.featureCard}>
                  <div className={styles.featureIconOrange}>C</div>
                  <div>
                    <div className={styles.featureTitle}>Campaign history persistence</div>
                    <div className={styles.featureDesc}>View and manage generated ad campaigns per user.</div>
                  </div>
                </div>

                <div className={styles.featureCard}>
                  <div className={styles.featureIconIndigo}>A</div>
                  <div>
                    <div className={styles.featureTitle}>AI workflow management</div>
                    <div className={styles.featureDesc}>Pipelines, job history, and secure studio access.</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <aside className={styles.authAside}>
            <div className={styles.loginPanel}>
              <div className={styles.loginHeader}>
                <div className={styles.loginTabs}>
                  <button
                    type="button"
                    onClick={() => setMode('login')}
                    className={mode === 'login' ? styles.loginTabActive : styles.loginTab}
                  >
                    Log in
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode('register')}
                    className={mode === 'register' ? styles.loginTabActiveAlt : styles.loginTab}
                  >
                    Create account
                  </button>
                </div>
                <div className={styles.loginModeLabel}>
                  {mode === 'login' ? 'Secure access' : 'New account'}
                </div>
              </div>

              <form onSubmit={handleSubmit} className={styles.loginForm}>
                {mode === 'register' && (
                  <div className={styles.loginField}>
                    <label className={styles.loginLabel}>Full name</label>
                    <input value={fullName} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFullName(e.target.value)} className={styles.loginInput} placeholder="Darshan" />
                  </div>
                )}

                <div className={styles.loginField}>
                  <label className={styles.loginLabel}>Email</label>
                  <input value={email} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)} type="email" className={styles.loginInput} placeholder="you@company.com" />
                </div>

                <div className={styles.loginField}>
                  <label className={styles.loginLabel}>Password</label>
                  <input value={password} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)} type="password" className={styles.loginInput} placeholder="••••••••" />
                </div>

                {error && <div className={styles.loginError}>{error}</div>}

                <button type="submit" disabled={loading} className={styles.loginSubmit}>
                  {loading ? 'Working...' : mode === 'login' ? 'Log in' : 'Create account'}
                </button>

                <button type="button" disabled className={styles.loginGoogleButton}>
                  <svg width="16" height="16" viewBox="0 0 48 48" fill="none"><path d="M44.5 20H24v8.5h11.8C34.2 34.4 29.6 38 24 38c-7.7 0-14-6.3-14-14s6.3-14 14-14c3.5 0 6.7 1.3 9.2 3.5l6.4-6.4C35.3 2.8 29.9 1 24 1 11.3 1 1 11.3 1 24s10.3 23 23 23 23-10.3 23-23c0-1.4-.1-2.8-.3-4z" fill="#4285F4"/></svg>
                  Continue with Google
                </button>

                <div className={styles.loginMetaRow}>
                  <div className={styles.loginMetaChip}>SQLite-backed auth</div>
                  <div className={styles.loginMetaChip}>JWT secured sessions</div>
                </div>
              </form>

            </div>
          </aside>

        </section>
      </main>
    </div>
  )
}
