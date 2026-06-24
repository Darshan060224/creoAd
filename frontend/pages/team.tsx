import React from 'react'
import PageShell from '../components/layout/PageShell'
import InviteBoard from '../components/invite/InviteBoard'

export default function TeamPage() {
  React.useEffect(() => {
    if (typeof window === 'undefined') return
    const token = window.localStorage.getItem('creoad_token')
    if (!token) window.location.href = '/login'
  }, [])

  return (
    <PageShell title="Team" subtitle="Invite collaborators and manage access.">
      <InviteBoard />
    </PageShell>
  )
}
