import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './app/App'
import { initTelegram } from './app/telegram'
import { EmptyState } from './components/ui'
import './index.css'

const env = initTelegram()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {env ? (
      <App env={env} />
    ) : (
      <EmptyState
        icon="📱"
        title="Telegram orqali oching"
        message="Bu ilova Telegram ichida ishlaydi. Klinika botidagi “Ochish” tugmasini bosing."
      />
    )}
  </StrictMode>,
)
