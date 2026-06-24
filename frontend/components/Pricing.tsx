import React from 'react'
import { useRouter } from 'next/router'
import styles from '../styles/landing.module.css'

interface PricingFeature {
  label: string
  highlight?: boolean
}

interface PricingPlan {
  name: string
  price: number | string
  subtext?: string
  desc: string
  features: PricingFeature[]
  hot?: boolean
  buttonLabel: string
  buttonStyle?: 'primary' | 'secondary' | 'dark'
}

const plans: PricingPlan[] = [
  {
    name: 'Starter',
    price: 0,
    subtext: '/mo',
    desc: 'For solo founders testing CreoAd.',
    features: [
      { label: '5 ads per month' },
      { label: '15s & 30s formats' },
      { label: 'MP4 export' },
      { label: 'Local AI included' }
    ],
    buttonLabel: 'Get started free',
    buttonStyle: 'secondary'
  },
  {
    name: 'Pro · Most popular',
    price: 49,
    subtext: '/mo',
    desc: 'For growing teams that need unlimited ad creation.',
    features: [
      { label: 'Unlimited ads' },
      { label: 'All formats + vertical' },
      { label: 'A/B creative variants' },
      { label: 'Team invite (5 seats)' },
      { label: 'Priority rendering' }
    ],
    hot: true,
    buttonLabel: 'Start Pro trial →',
    buttonStyle: 'primary'
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    desc: 'For agencies on Oracle Cloud OCI.',
    features: [
      { label: 'Oracle Cloud deploy', highlight: true },
      { label: 'Dedicated GPU', highlight: true },
      { label: 'White-label', highlight: true },
      { label: 'SLA + support', highlight: true },
      { label: 'Unlimited seats', highlight: true }
    ],
    buttonLabel: 'Book a demo',
    buttonStyle: 'dark'
  }
]

export default function Pricing() {
  return (
    <section className={`${styles.section}`}>
      <div className={styles.secLabel}>Pricing</div>
      <h2 className={styles.secTitle}>
        SIMPLE <span>PRICING</span>
      </h2>
      <p className={styles.secSub}>
        No per-generation fees. No API charges. Pay once, generate unlimited ads locally.
      </p>

      <div className={styles.planGrid}>
        {plans.map((plan, idx) => (
          <PricingCard key={idx} plan={plan} />
        ))}
      </div>
    </section>
  )
}

interface PricingCardProps {
  plan: PricingPlan
}

function PricingCard({ plan }: PricingCardProps) {
  const router = useRouter()
  const planClass = plan.hot ? styles.hot : ''
  const buttonClass = plan.buttonStyle === 'primary'
    ? `${styles.btn} ${styles.btnPrimary}`
    : plan.buttonStyle === 'dark'
      ? `${styles.btn} ${styles.btnDark}`
      : `${styles.btn} ${styles.btnSecondary}`

  return (
    <div className={`${styles.plan} ${planClass}`}>
      <div className={styles.planName}>
        {plan.name}
      </div>

      <div className={styles.planPrice}>
        {plan.price}
        {plan.subtext && <sub>{plan.subtext}</sub>}
      </div>

      <div className={styles.planDesc}>
        {plan.desc}
      </div>

      <div className={styles.planFeats}>
        {plan.features.map((feature, idx) => (
          <div key={idx} className={styles.pf}>
            <div className={styles.pfDot} style={
              feature.highlight && plan.hot ? { background: '#818cf8' } :
              feature.highlight ? { background: '#ff5c00' } :
              {}
            }></div>
            {feature.label}
          </div>
        ))}
      </div>

      <button
        onClick={() => router.push('/studio')}
        className={buttonClass}
        style={{ width: '100%', justifyContent: 'center', marginTop: 'auto' }}
      >
        {plan.buttonLabel}
      </button>
    </div>
  )
}
