import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { api, unwrap } from '../../api/client'
import { useSession } from '../../app/auth'
import { Card, Page, StatusBadge } from '../../components/ui'
import { formatDateTime } from '../../lib/format'

const ACTIONS = [
  { to: '/services', icon: '🦷', title: 'Qabulga yozilish', hint: 'Xizmat, kun va vaqtni tanlang' },
  { to: '/services', icon: '💳', title: 'Xizmatlar va narxlar', hint: "Barcha narxlar so'mda" },
  {
    to: '/my-bookings',
    icon: '📅',
    title: 'Mening qabullarim',
    hint: "Holatini ko'rish va bekor qilish",
  },
  { to: '/chat', icon: '💬', title: 'Savol berish', hint: 'AI yordamchi va operator' },
]

export function HomePage() {
  const session = useSession()
  const navigate = useNavigate()
  const bookings = useQuery({
    queryKey: ['my-bookings'],
    queryFn: () => unwrap(api.GET('/v1/bookings/me')),
  })
  const next = bookings.data
    ?.filter((b) => b.status !== 'cancelled' && new Date(b.starts_at) > new Date())
    .sort((a, b) => a.starts_at.localeCompare(b.starts_at))[0]
  const firstName = session.customer.name?.split(' ')[0]

  return (
    <Page
      title={session.tenant.name}
      subtitle={`Assalomu alaykum${firstName ? `, ${firstName}` : ''}!`}
    >
      {next && (
        <Card onClick={() => navigate('/my-bookings')} testId="next-booking">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase text-hint">Keyingi qabul</span>
            <StatusBadge status={next.status} />
          </div>
          <p className="mt-1 font-semibold">{next.service.name}</p>
          <p className="text-sm text-hint">{formatDateTime(next.starts_at)}</p>
        </Card>
      )}
      <div className="grid grid-cols-2 gap-3">
        {ACTIONS.map((a) => (
          <Card key={a.title} onClick={() => navigate(a.to)} testId={`home-${a.to.slice(1)}`}>
            <div className="text-2xl">{a.icon}</div>
            <p className="mt-2 font-semibold leading-tight">{a.title}</p>
            <p className="mt-0.5 text-xs text-hint">{a.hint}</p>
          </Card>
        ))}
      </div>
    </Page>
  )
}
