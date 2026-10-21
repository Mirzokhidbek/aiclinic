import {
  backButton,
  hapticFeedback,
  init,
  mainButton,
  miniApp,
  mockTelegramEnv,
  retrieveLaunchParams,
  retrieveRawInitData,
  themeParams,
  viewport,
} from '@telegram-apps/sdk-react'

export interface TelegramEnv {
  /** Running inside a real Telegram client (not a plain browser tab). */
  native: boolean
  rawInitData: string
  startParam?: string
  firstName?: string
}

function isInsideTelegram(): boolean {
  return window.parent !== window || 'TelegramWebviewProxy' in window
}

/**
 * Initialise the Telegram SDK. Outside Telegram (local dev, Playwright) the launch params come
 * from the URL hash and Telegram methods become no-ops, so the same code path is exercised.
 * Returns null when no launch params are available at all (page opened directly).
 */
export function initTelegram(): TelegramEnv | null {
  const native = isInsideTelegram()
  if (!native) {
    const hash = window.location.hash.slice(1)
    if (!hash.includes('tgWebAppData')) {
      try {
        retrieveLaunchParams() // may be cached in sessionStorage from an earlier load
      } catch {
        return null
      }
    } else {
      mockTelegramEnv({ launchParams: hash, onEvent: () => {}, resetPostMessage: true })
    }
  }

  let rawInitData: string | undefined
  let startParam: string | undefined
  let firstName: string | undefined
  try {
    const lp = retrieveLaunchParams(true)
    rawInitData = retrieveRawInitData()
    startParam = lp.tgWebAppStartParam
    firstName = lp.tgWebAppData?.user?.firstName
  } catch {
    return null
  }
  if (!rawInitData) return null

  init()
  backButton.mount.ifAvailable()
  mainButton.mount.ifAvailable()
  themeParams.mountSync.ifAvailable()
  themeParams.bindCssVars.ifAvailable()
  miniApp.mountSync.ifAvailable()
  miniApp.ready.ifAvailable()
  viewport.expand.ifAvailable()

  return { native, rawInitData, startParam, firstName }
}

export const haptics = {
  success: () => hapticFeedback.notificationOccurred.ifAvailable('success'),
  error: () => hapticFeedback.notificationOccurred.ifAvailable('error'),
  select: () => hapticFeedback.selectionChanged.ifAvailable(),
}
