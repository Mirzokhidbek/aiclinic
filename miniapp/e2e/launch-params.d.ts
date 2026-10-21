declare module '*/launch-params.mjs' {
  export function launchHash(opts?: {
    userId?: number
    firstName?: string
    botToken?: string
  }): string
}
