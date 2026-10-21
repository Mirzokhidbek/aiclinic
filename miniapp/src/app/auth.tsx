import { useQuery } from '@tanstack/react-query'
import { createContext, useContext, type ReactNode } from 'react'

import { api, setAccessToken, unwrap, type AuthResult } from '../api/client'
import { ErrorState, FullScreenSpinner } from '../components/ui'
import type { TelegramEnv } from './telegram'

const AuthContext = createContext<AuthResult | null>(null)

function tenantSlug(env: TelegramEnv): string {
  const fromQuery = new URLSearchParams(window.location.search).get('tenant')
  return fromQuery ?? env.startParam ?? import.meta.env.VITE_TENANT_SLUG ?? 'nur-klinika'
}

export function AuthProvider({ env, children }: { env: TelegramEnv; children: ReactNode }) {
  const login = useQuery({
    queryKey: ['auth', env.rawInitData],
    queryFn: async () => {
      const result = await unwrap(
        api.POST('/v1/auth/telegram', {
          body: { init_data: env.rawInitData, tenant_slug: tenantSlug(env) },
        }),
      )
      setAccessToken(result.access_token)
      return result
    },
    staleTime: Infinity,
    retry: 1,
  })

  if (login.isPending) return <FullScreenSpinner />
  if (login.isError)
    return (
      <ErrorState
        title="Kirish amalga oshmadi"
        message={login.error.message}
        onRetry={() => login.refetch()}
      />
    )
  return <AuthContext.Provider value={login.data}>{children}</AuthContext.Provider>
}

export function useSession(): AuthResult {
  const session = useContext(AuthContext)
  if (!session) throw new Error('useSession must be used inside AuthProvider')
  return session
}
