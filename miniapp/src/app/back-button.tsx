import { backButton } from '@telegram-apps/sdk-react'
import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

/** Telegram BackButton on every screen except home; in a browser a small header link. */
export function BackButtonBridge({ native }: { native: boolean }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const isRoot = pathname === '/'

  useEffect(() => {
    if (!native) return
    if (isRoot) {
      backButton.hide.ifAvailable()
      return
    }
    backButton.show.ifAvailable()
    const [subscribed, off] = backButton.onClick.ifAvailable(() => navigate(-1))
    return () => {
      if (subscribed) off()
    }
  }, [native, isRoot, navigate])

  if (native || isRoot) return null
  return (
    <button
      type="button"
      onClick={() => navigate(-1)}
      className="px-4 pt-3 text-sm text-link"
      data-testid="back-button"
    >
      ← Orqaga
    </button>
  )
}
