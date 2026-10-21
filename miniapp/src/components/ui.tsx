import type { ReactNode } from 'react'

export function Page({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: ReactNode
  children: ReactNode
}) {
  return (
    <main className="mx-auto max-w-xl px-4 pt-3 pb-28">
      <h1 className="text-2xl font-bold">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-hint">{subtitle}</p>}
      <div className="mt-4 space-y-3">{children}</div>
    </main>
  )
}

export function Card({
  children,
  onClick,
  testId,
}: {
  children: ReactNode
  onClick?: () => void
  testId?: string
}) {
  const className = 'block w-full rounded-2xl bg-section p-4 text-left'
  return onClick ? (
    <button
      type="button"
      onClick={onClick}
      className={`${className} active:opacity-70`}
      data-testid={testId}
    >
      {children}
    </button>
  ) : (
    <div className={className} data-testid={testId}>
      {children}
    </div>
  )
}

export function Chip({
  active,
  children,
  onClick,
  testId,
}: {
  active: boolean
  children: ReactNode
  onClick: () => void
  testId?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      aria-pressed={active}
      className={`shrink-0 rounded-full px-3.5 py-1.5 text-sm font-medium ${
        active ? 'bg-button text-button-text' : 'bg-section text-text'
      }`}
    >
      {children}
    </button>
  )
}

const BADGE_STYLES: Record<string, string> = {
  pending: 'bg-amber-500/15 text-amber-600',
  confirmed: 'bg-emerald-500/15 text-emerald-600',
  cancelled: 'bg-hint/15 text-hint',
}

const BADGE_LABELS: Record<string, string> = {
  pending: 'Tasdiqlanmagan',
  confirmed: 'Tasdiqlangan',
  cancelled: 'Bekor qilingan',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${BADGE_STYLES[status] ?? ''}`}
    >
      {BADGE_LABELS[status] ?? status}
    </span>
  )
}

export function Skeleton({ className = 'h-20' }: { className?: string }) {
  return <div className={`animate-pulse rounded-2xl bg-section ${className}`} aria-hidden />
}

export function SkeletonList({ count = 4, className }: { count?: number; className?: string }) {
  return (
    <div className="space-y-3" data-testid="skeleton">
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} className={className} />
      ))}
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  message,
  action,
}: {
  icon: string
  title: string
  message?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center" data-testid="empty-state">
      <div className="text-5xl">{icon}</div>
      <p className="mt-3 font-semibold">{title}</p>
      {message && <p className="mt-1 text-sm text-hint">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({
  title = 'Nimadir xato ketdi',
  message,
  onRetry,
}: {
  title?: string
  message?: string
  onRetry?: () => void
}) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center" data-testid="error-state">
      <div className="text-5xl">⚠️</div>
      <p className="mt-3 font-semibold">{title}</p>
      {message && <p className="mt-1 text-sm text-hint">{message}</p>}
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-4 text-sm font-medium text-link">
          Qayta urinish
        </button>
      )}
    </div>
  )
}

export function FullScreenSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center" data-testid="spinner">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-hint/30 border-t-button" />
    </div>
  )
}

export function LinkButton({
  children,
  onClick,
  destructive,
  testId,
}: {
  children: ReactNode
  onClick: () => void
  destructive?: boolean
  testId?: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      className={`text-sm font-medium ${destructive ? 'text-destructive' : 'text-link'}`}
    >
      {children}
    </button>
  )
}
