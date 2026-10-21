import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api, unwrap } from '../../api/client'
import { haptics } from '../../app/telegram'
import { Card, Chip, EmptyState, ErrorState, Page, SkeletonList } from '../../components/ui'
import { formatPrice } from '../../lib/format'

export function ServicesPage() {
  const navigate = useNavigate()
  const [category, setCategory] = useState<string | null>(null)
  const services = useQuery({
    queryKey: ['services'],
    queryFn: () => unwrap(api.GET('/v1/services')),
  })

  const categories = [...new Set(services.data?.map((s) => s.category))]
  const visible = services.data?.filter((s) => !category || s.category === category) ?? []

  return (
    <Page title="Xizmatlar" subtitle="Xizmatni tanlang va qulay vaqtga yoziling">
      {services.isPending && <SkeletonList count={5} />}
      {services.isError && (
        <ErrorState message={services.error.message} onRetry={() => services.refetch()} />
      )}
      {services.isSuccess && services.data.length === 0 && (
        <EmptyState icon="🗂️" title="Hozircha xizmatlar yo'q" />
      )}
      {services.isSuccess && services.data.length > 0 && (
        <>
          <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1">
            <Chip active={category === null} onClick={() => setCategory(null)}>
              Barchasi
            </Chip>
            {categories.map((c) => (
              <Chip
                key={c}
                active={category === c}
                onClick={() => {
                  haptics.select()
                  setCategory(c)
                }}
                testId={`category-${c}`}
              >
                {c}
              </Chip>
            ))}
          </div>
          {visible.map((s) => (
            <Card key={s.id} onClick={() => navigate(`/book/${s.id}`)} testId="service-card">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">{s.name}</p>
                  <p className="mt-0.5 text-xs text-hint">
                    {s.category} · {s.duration_min} daqiqa
                  </p>
                  {s.description && <p className="mt-1.5 text-sm text-hint">{s.description}</p>}
                </div>
                <p className="shrink-0 font-semibold text-accent">{formatPrice(s.price_uzs)}</p>
              </div>
            </Card>
          ))}
        </>
      )}
    </Page>
  )
}
