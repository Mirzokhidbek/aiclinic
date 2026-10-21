import { closeMiniApp } from '@telegram-apps/sdk-react'

import { EmptyState, LinkButton, Page } from '../../components/ui'

/** In-app AI chat arrives with M5 (SSE streaming). Until then the bot chat is the entry point. */
export function ChatPage() {
  return (
    <Page title="Savol berish">
      <EmptyState
        icon="💬"
        title="Chat tez orada shu yerda bo'ladi"
        message="Hozircha savollaringizni bot chatiga yozing: yordamchi yoki operator javob beradi."
        action={
          <LinkButton onClick={() => closeMiniApp.ifAvailable()}>Bot chatiga qaytish</LinkButton>
        }
      />
    </Page>
  )
}
