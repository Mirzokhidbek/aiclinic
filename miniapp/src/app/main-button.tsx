import { mainButton } from '@telegram-apps/sdk-react'
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react'

export interface MainButtonConfig {
  text: string
  onClick: () => void
  enabled?: boolean
  loading?: boolean
}

type Setter = (config: MainButtonConfig | null) => void
const MainButtonContext = createContext<Setter>(() => {})

/**
 * Telegram's MainButton inside Telegram; an equivalent in-page button in a plain browser
 * (local dev and Playwright), so both paths share the same screen logic.
 */
export function MainButtonProvider({ native, children }: { native: boolean; children: ReactNode }) {
  const [config, setConfig] = useState<MainButtonConfig | null>(null)

  useEffect(() => {
    if (!native) return
    if (!config) {
      mainButton.setParams.ifAvailable({ isVisible: false })
      return
    }
    mainButton.setParams.ifAvailable({
      text: config.text,
      isVisible: true,
      isEnabled: config.enabled !== false && !config.loading,
      isLoaderVisible: !!config.loading,
    })
    const [subscribed, off] = mainButton.onClick.ifAvailable(config.onClick)
    return () => {
      if (subscribed) off()
    }
  }, [native, config])

  return (
    <MainButtonContext.Provider value={setConfig}>
      {children}
      {!native && config && (
        <div className="fixed inset-x-0 bottom-0 bg-bg p-3 shadow-[0_-1px_0_var(--color-separator)]">
          <button
            type="button"
            data-testid="main-button"
            onClick={config.onClick}
            disabled={config.enabled === false || config.loading}
            className="w-full rounded-xl bg-button py-3.5 font-semibold text-button-text disabled:opacity-50"
          >
            {config.loading ? '…' : config.text}
          </button>
        </div>
      )}
    </MainButtonContext.Provider>
  )
}

/** Show the main button while the calling screen is mounted. Pass null to hide it. */
export function useMainButton(config: MainButtonConfig | null): void {
  const set = useContext(MainButtonContext)
  const onClickRef = useRef(config?.onClick)
  useEffect(() => {
    onClickRef.current = config?.onClick
  })
  const text = config?.text
  const enabled = config?.enabled
  const loading = config?.loading
  const visible = config !== null

  useEffect(() => {
    set(visible && text ? { text, enabled, loading, onClick: () => onClickRef.current?.() } : null)
  }, [set, visible, text, enabled, loading])

  useEffect(() => () => set(null), [set])
}
