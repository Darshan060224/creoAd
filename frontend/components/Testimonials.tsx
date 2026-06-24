import React from 'react'
import styles from '../styles/landing.module.css'

interface Testimonial {
  author: string
  initials: string
  role: string
  text: string
  rating: number
}

const testimonials: Testimonial[] = [
  {
    author: 'Tim Morris',
    initials: 'TM',
    role: 'Founder @ SotaClothing',
    text: "CreoAd generated a TV-ready ad from my URL in 90 seconds. I didn't touch a single script or image.",
    rating: 5
  },
  {
    author: 'Jasmine A.',
    initials: 'JA',
    role: 'Head of Growth @ Sijo',
    text: "Running 100% local means our brand data never leaves our server. That's a game-changer for enterprise.",
    rating: 5
  },
  {
    author: 'Raj K.',
    initials: 'RK',
    role: 'Marketing Lead @ Petfolk',
    text: "We generate 40+ ad variants a week. The Oracle Cloud deployment scales perfectly with our volume.",
    rating: 5
  }
]

export default function Testimonials() {
  return (
    <section className={`${styles.section} ${styles.gridBg}`}>
      <div className={styles.secLabel}>Customers</div>
      <h2 className={styles.secTitle}>
        LOVED BY <span>MARKETERS</span>
      </h2>
      <p className={styles.secSub} style={{ marginBottom: '28px' }}>
        Real results from teams using CreoAd to generate TV-ready ads at scale.
      </p>

      <div className={styles.testiGrid}>
        {testimonials.map((testimonial, idx) => (
          <TestiCard key={idx} testimonial={testimonial} />
        ))}
      </div>
    </section>
  )
}

interface TestiCardProps {
  testimonial: Testimonial
}

function TestiCard({ testimonial }: TestiCardProps) {
  return (
    <div className={styles.tcard}>
      <div className={styles.tcardStars}>
        {'★'.repeat(testimonial.rating)}
      </div>
      <div className={styles.tcardQ}>
        &ldquo;{testimonial.text}&rdquo;
      </div>
      <div className={styles.tcardAuthor}>
        <div className={styles.tav}>
          {testimonial.initials}
        </div>
        <div>
          <div className={styles.tavName}>{testimonial.author}</div>
          <div className={styles.tavRole}>{testimonial.role}</div>
        </div>
      </div>
    </div>
  )
}
