import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { api, ApiError, unwrap, type Booking } from '../../api/client'
import { useMainButton } from '../../app/main-button'
import { haptics } from '../../app/telegram'
import { Card, EmptyState, ErrorState, Page, SkeletonList, StatusBadge } from '../../components/ui'
import { formatDateTime, formatPrice, minutesLeft } from '../../lib/format'

function useMinutesLeft(iso: string | null | undefined): number | null {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!iso) return
    const id = window.setInterval(() => setNow(Date.now()), 15_000)
    return () => window.clearInterval(id)
  }, [iso])
  return iso ? minutesLeft(iso, now) : null
}

function Summary({ booking }: { booking: Booking }) {
  return (
    <Card testId="booking-summary">
      <div className="flex items-center justify-between">
        <p className="font-semibold">{booking.service.name}</p>
        <StatusBadge status={booking.status} />
      </div>
      <p className="mt-2 text-sm">🕐 {formatDateTime(booking.starts_at)}</p>
      <p className="mt-1 text-sm">💳 {formatPrice(booking.service.price_uzs)}</p>
      <p className="mt-1 text-sm">⏱ {booking.service.duration_min} daqiqa</p>
    </Card>
  )
}

export function BookingPage() {
  const { id = '' } = useParams()
  const [search] = useSearchParams()
  const token = search.get('t') ?? ''
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const booking = useQuery({
    queryKey: ['booking', id],
    queryFn: () =>
      unwrap(api.GET('/v1/bookings/{booking_id}', { params: { path: { booking_id: id } } })),
  })

  const confirm = useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/v1/bookings/{booking_id}/confirm', {
          params: { path: { booking_id: id } },
          body: { confirm_token: token },
        }),
      ),
    onSuccess: (data) => {
      haptics.success()
      queryClient.setQueryData(['booking', id], data)
      queryClient.invalidateQueries({ queryKey: ['my-bookings'] })
    },
    onError: () => {
      haptics.error()
      booking.refetch()
    },
  })

  const data = booking.data
  const left = useMinutesLeft(data?.status === 'pending' ? data.expires_at : null)
  const canConfirm = data?.status === 'pending' && !!token && left !== 0

  useMainButton(
    canConfirm
      ? { text: 'Tasdiqlash', onClick: () => confirm.mutate(), loading: confirm.isPending }
      : data?.status === 'confirmed'
        ? { text: 'Mening qabullarim', onClick: () => navigate('/my-bookings') }
        : null,
  )

  if (booking.isPending)
    return (
      <Page title="Qabul">
        <SkeletonList count={1} className="h-36" />
      </Page>
    )
  if (booking.isError)
    return (
      <Page title="Qabul">
        {booking.error instanceof ApiError && booking.error.status === 404 ? (
          <EmptyState icon="🔍" title="Qabul topilmadi" />
        ) : (
          <ErrorState message={booking.error.message} onRetry={() => booking.refetch()} />
        )}
      </Page>
    )

  const b = booking.data
  const expired = b.status === 'cancelled' || (b.status === 'pending' && left === 0)
  return (
    <Page
      title={
        b.status === 'confirmed'
          ? 'Qabul tasdiqlandi ✅'
          : expired
            ? 'Qabul faol emas'
            : 'Qabulni tasdiqlang'
      }
      subtitle={
        b.status === 'confirmed'
          ? "Sizni kutib qolamiz! Rejangiz o'zgarsa, qabulni bekor qilishingiz mumkin."
          : expired
            ? 'Band qilish muddati tugagan yoki bekor qilingan.'
            : left !== null
              ? `Vaqt siz uchun ${left} daqiqa band qilib turiladi.`
              : undefined
      }
    >
      <Summary booking={b} />
      {confirm.isError && (
        <p className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive" role="alert">
          {confirm.error.message}
        </p>
      )}
      {b.status === 'pending' && !token && !expired && (
        <p className="text-sm text-hint">
          Tasdiqlash uchun botdagi havoladan foydalaning yoki qayta yoziling.
        </p>
      )}
      {expired && (
        <button
          type="button"
          onClick={() => navigate(`/book/${b.service.id}`, { replace: true })}
          className="text-sm font-medium text-link"
        >
          Boshqa vaqtni tanlash
        </button>
      )}
    </Page>
  )
}
