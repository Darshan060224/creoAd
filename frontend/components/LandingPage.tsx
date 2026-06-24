import React from 'react'
import Navigation from './Navigation'
import Hero from './Hero'
import LogoTrust from './LogoTrust'
import HowItWorks from './HowItWorks'
import Features from './Features'
import Pricing from './Pricing'
import Testimonials from './Testimonials'
import CTABanner from './CTABanner'
import Footer from './Footer'

export default function LandingPage() {
  return (
    <main>
      <Navigation />
      <Hero />
      <div id="features">
        <LogoTrust />
      </div>
      <div id="how">
        <HowItWorks />
      </div>
      <Features />
      <div id="pricing">
        <Pricing />
      </div>
      <div id="testimonials">
        <Testimonials />
      </div>
      <CTABanner />
      <Footer />
    </main>
  )
}
