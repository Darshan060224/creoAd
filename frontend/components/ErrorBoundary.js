import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    if (typeof console !== 'undefined') {
      console.error('Frontend error boundary caught an error:', error, errorInfo)
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
    if (typeof this.props.onReset === 'function') {
      this.props.onReset()
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '24px', background: '#f0f0ee', color: '#0a0a0a' }}>
          <div style={{ maxWidth: 560, width: '100%', background: '#fff', border: '1px solid #e0e0dc', borderRadius: 16, padding: 24, boxShadow: '0 16px 40px rgba(0,0,0,.08)' }}>
            <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#ff5c00', marginBottom: 8 }}>
              UI fallback
            </div>
            <h1 style={{ margin: '0 0 12px', fontSize: 28, lineHeight: 1.1 }}>Something broke in the interface.</h1>
            <p style={{ margin: '0 0 20px', color: '#555', lineHeight: 1.6 }}>
              The page hit an unexpected rendering error. The app kept running, and you can try reloading the view.
            </p>
            <button
              type="button"
              onClick={this.handleReset}
              style={{ border: 'none', borderRadius: 10, padding: '12px 16px', background: '#ff5c00', color: '#fff', fontWeight: 700, cursor: 'pointer' }}
            >
              Try again
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
