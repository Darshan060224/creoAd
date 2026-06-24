import '../styles/globals.css'
import Head from 'next/head'
import ErrorBoundary from '../components/ErrorBoundary.js'


export default function App({ Component, pageProps }) {
  return (
    <ErrorBoundary>
      <Head>
        <title>CreoAd — Self-Hosted AI Ad Generation Studio</title>
        <meta name="description" content="Paste a business URL and let CreoAd handle scrape, script, visuals, voice, and render in one self-hosted AI flow." />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
      </Head>
      <Component {...pageProps} />
    </ErrorBoundary>
  )
}

