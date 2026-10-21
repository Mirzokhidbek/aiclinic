import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { api, ApiError, unwrap } from '../../api/client'
import { useMainButton } from '../../app/main-button'
import { haptics } from '../../app/telegram'
import { Chip, EmptyState, ErrorState, Page, Skeleton, SkeletonList } from '../../components/ui'
import { formatPrice, formatTime, nextDays } from '../../lib/format'

const DAYS_AHEAD = 14

export function BookPage() {
  const { serviceId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const days = useMemo(() => nextDays(DAYS_AHEAD), [])
  const [day, setDay] = useState(days[0].iso)
  const [slotId, setSlotId] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  // One key per chosen slot: retries of the same choice can't create two bookings.
  const idempotencyKey = useMemo(() => (slotId ? crypto.randomUUID() : ''), [slotId])

  const availability = useQuery({
    queryKey: ['availability', serviceId, day],
    queryFn: () =>
      unwrap(
        api.GET('/v1/services/{service_id}/availability', {
          params: { path: { service_id: serviceId }, query: { date: day } },
        }),
      ),
  })

  const book = useMutation({
    mutationFn: (slot: string) =>
      unwrap(
        api.POST('/v1/bookings', {
          body: { slot_id: slot },
          params: { header: { 'Idempotency-Key': idempotencyKey } },
        }),
      ),
    onSuccess: (booking) => {
      haptics.success()
      queryClient.invalidateQueries({ queryKey: ['my-bookings'] })
      navigate(`/booking/${booking.id}?t=${encodeURIComponent(booking.confirm_token ?? '')}`)
    },
    onError: (error) => {
      haptics.error()
      setSlotId(null)
      setNotice(
        error instanceof ApiError && error.code === 'slot_full'
          ? 'Bu vaqt hozirgina band qilindi. Boshqa vaqtni tanlang.'
          : error.message,
      )
      queryClient.invalidateQueries({ queryKey: ['availability', serviceId, day] })
    },
  })

  const selected = availability.data?.slots.find((s) => s.id === slotId)
  useMainButton(
    selected
      ? {
          text: `Davom etish · ${formatTime(selected.starts_at)}`,
          onClick: () => book.mutate(selected.id),
          loading: book.isPending,
        }
      : null,
  )

  const service = availability.data?.service
  return (
    <Page
      title={service?.name ?? 'Vaqtni tanlang'}
      subtitle={
        service ? `${formatPrice(service.price_uzs)} · ${service.duration_min} daqiqa` : undefined
      }
    >
      <div
        className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1"
        data-testid="day-picker"
      >
        {days.map((d) => (
          <button
            key={d.iso}
            type="button"
            data-testid={`day-${d.iso}`}
            aria-pressed={d.iso === day}
            onClick={() => {
              haptics.select()
              setDay(d.iso)
              setSlotId(null)
              setNotice(null)
            }}
            className={`flex w-14 shrink-0 flex-col items-center rounded-2xl py-2 ${
              d.iso === day ? 'bg-button text-button-text' : 'bg-section'
            }`}
          >
            <span className="text-xs opacity-80">{d.weekday}</span>
            <span className="text-lg font-semibold">{d.day}</span>
          </button>
        ))}
      </div>

      {notice && (
        <p className="rounded-xl bg-destructive/10 p-3 text-sm text-destructive" role="alert">
          {notice}
        </p>
      )}

      {availability.isPending && (
        <>
          <Skeleton className="h-6 w-32" />
          <SkeletonList count={2} className="h-12" />
        </>
      )}
      {availability.isError && (
        <ErrorState message={availability.error.message} onRetry={() => availability.refetch()} />
      )}
      {availability.isSuccess && availability.data.slots.length === 0 && (
        <EmptyState
          icon="🗓️"
          title="Bu kunga bo'sh vaqt yo'q"
          message="Boshqa kunni tanlab ko'ring."
        />
      )}
      {availability.isSuccess && availability.data.slots.length > 0 && (
        <div className="grid grid-cols-4 gap-2" data-testid="slots">
          {availability.data.slots.map((s) => (
            <Chip
              key={s.id}
              active={s.id === slotId}
              onClick={() => {
                haptics.select()
                setSlotId(s.id)
                setNotice(null)
              }}
              testId="slot"
            >
              {formatTime(s.starts_at)}
            </Chip>
          ))}
        </div>
      )}
    </Page>
  )
}
