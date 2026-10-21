import createClient, { type Middleware } from 'openapi-fetch'

import type { components, paths } from './schema'

export type Service = components['schemas']['ServiceOut']
export type Slot = components['schemas']['SlotOut']
export type Booking = components['schemas']['BookingOut']
export type Availability = components['schemas']['AvailabilityOut']
export type AuthResult = components['schemas']['AuthOut']

/** Error returned by the API as {"error": {"code", "message"}}. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

// Kept in memory only: nothing sensitive goes to localStorage.
let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

const auth: Middleware = {
  onRequest({ request }) {
    if (accessToken) request.headers.set('Authorization', `Bearer ${accessToken}`)
    return request
  },
}

export const api = createClient<paths>({ baseUrl: import.meta.env.VITE_API_URL ?? '' })
api.use(auth)

interface Result<T> {
  data?: T
  error?: unknown
  response: Response
}

/** Return data or throw an ApiError with the server's error code. */
export async function unwrap<T>(call: Promise<Result<T>>): Promise<T> {
  let result: Result<T>
  try {
    result = await call
  } catch {
    throw new ApiError(0, 'network_error', 'Internetga ulanishni tekshiring')
  }
  if (result.data !== undefined && result.response.ok) return result.data
  const body = result.error as { error?: { code?: string; message?: string } } | undefined
  throw new ApiError(
    result.response.status,
    body?.error?.code ?? 'unknown_error',
    body?.error?.message ?? 'Kutilmagan xatolik',
  )
}
