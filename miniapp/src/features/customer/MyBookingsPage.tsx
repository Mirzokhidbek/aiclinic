import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api, unwrap, type Booking } from '../../api/client'
import { haptics } from '../../app/telegram'
import {
  Card,
  EmptyState,
  ErrorState,
  LinkButton,
  Page,
  SkeletonList,
  StatusBadge,
} from '../../components/ui'
import { formatDateTime, formatPrice } from '../../lib/format'

function BookingCard({ booking, upcoming }: { booking: Booking; upcoming: boolean }) {
  const queryClient = useQueryClient()
  const [asking, setAsking] = useState(false)
  const cancel = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/v1/bookings/{booking_id}/cancel', {
          params: { path: { booking_id: booking.id } },
        }),
      ),
    onSuccess: () => {
      haptics.success()
      queryClient.invalidateQueries({ queryKey: ['my-bookings'] })
      queryClient.invalidateQueries({ queryKey: ['availability'] })
    },
    onError: () => haptics.error(),
  })

  return (
    <Card testId="booking-card">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold">{booking.service.name}</p>
          <p className="mt-0.5 text-sm text-hint">{formatDateTime(booking.starts_at)}</p>
          <p className="mt-0.5 text-sm text-hint">{formatPrice(booking.service.price_uzs)}</p>
        </div>
        <StatusBadge status={booking.status} />
      </div>
      {cancel.isError && <p className="mt-2 text-sm text-destructive">{cancel.error.message}</p>}
      {upcoming && booking.status !== 'cancelled' && (
        <div className="mt-3 flex gap-4">
          {asking ? (
            <>
              <LinkButton destructive onClick={() => cancel.mutate()} testId="confirm-cancel">
                {cancel.isPending ? 'Bekor qilinmoqda…' : 'Ha, bekor qilish'}
              </LinkButton>
              <LinkButton onClick={() => setAsking(false)}>Yo'q</LinkButton>
            </>
          ) : (
            <LinkButton destructive onClick={() => setAsking(true)} testId="cancel-booking">
              Bekor qilish
            </LinkButton>
          )}
        </div>
      )}
    </Card>
  )
}

export function MyBookingsPage() {
  const navigate = useNavigate()
  const bookings = useQuery({
    queryKey: ['my-bookings'],
    queryFn: () => unwrap(api.GET('/v1/bookings/me')),
  })

  const now = new Date()
  const upcoming = (bookings.data ?? [])
    .filter((b) => new Date(b.starts_at) > now && b.status !== 'cancelled')
    .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
  const history = (bookings.data ?? []).filter((b) => !upcoming.includes(b))

  return (
    <Page title="Mening qabullarim">
      {bookings.isPending && <SkeletonList count={3} />}
      {bookings.isError && (
        <ErrorState message={bookings.error.message} onRetry={() => bookings.refetch()} />
      )}
      {bookings.isSuccess && bookings.data.length === 0 && (
        <EmptyState
          icon="📅"
          title="Hali qabullar yo'q"
          message="Xizmatni tanlang va o'zingizga qulay vaqtga yoziling."
          action={<LinkButton onClick={() => navigate('/services')}>Qabulga yozilish</LinkButton>}
        />
      )}
      {upcoming.length > 0 && (
        <section className="space-y-3" data-testid="upcoming">
          <h2 className="text-sm font-medium uppercase text-hint">Kelgusi</h2>
          {upcoming.map((b) => (
            <BookingCard key={b.id} booking={b} upcoming />
          ))}
        </section>
      )}
      {history.length > 0 && (
        <section className="space-y-3" data-testid="history">
          <h2 className="pt-2 text-sm font-medium uppercase text-hint">Tarix</h2>
          {history.map((b) => (
            <BookingCard key={b.id} booking={b} upcoming={false} />
          ))}
        </section>
      )}
    </Page>
  )
}
