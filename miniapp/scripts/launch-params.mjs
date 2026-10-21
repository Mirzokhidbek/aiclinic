// Build Telegram Mini App launch params (signed initData) for local dev and Playwright.
// Signing uses the tenant's bot token, so the backend accepts it exactly like real Telegram.
import { createHmac } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

export function botTokenFromEnv(envPath = resolve(import.meta.dirname, '../../.env')) {
  if (process.env.TELEGRAM_BOT_TOKEN) return process.env.TELEGRAM_BOT_TOKEN
  const line = readFileSync(envPath, 'utf8')
    .split('\n')
    .find((l) => l.startsWith('TELEGRAM_BOT_TOKEN='))
  const token = line?.slice('TELEGRAM_BOT_TOKEN='.length).trim()
  if (!token) throw new Error('TELEGRAM_BOT_TOKEN not found in env or .env')
  return token
}

export function signInitData(fields, botToken) {
  const check = Object.keys(fields)
    .sort()
    .map((k) => `${k}=${fields[k]}`)
    .join('\n')
  const secret = createHmac('sha256', 'WebAppData').update(botToken).digest()
  const hash = createHmac('sha256', secret).update(check).digest('hex')
  return new URLSearchParams({ ...fields, hash }).toString()
}

const LIGHT_THEME = {
  bg_color: '#ffffff',
  secondary_bg_color: '#f1f1f4',
  section_bg_color: '#ffffff',
  text_color: '#000000',
  hint_color: '#8e8e93',
  link_color: '#2481cc',
  button_color: '#2481cc',
  button_text_color: '#ffffff',
  accent_text_color: '#2481cc',
  destructive_text_color: '#e53935',
  section_separator_color: '#e5e5ea',
}

/** URL hash with tgWebApp* launch params for a fake Telegram user. */
export function launchHash({
  userId = 777000001,
  firstName = 'Test',
  botToken,
  theme = LIGHT_THEME,
} = {}) {
  const initData = signInitData(
    {
      auth_date: String(Math.floor(Date.now() / 1000)),
      query_id: 'AAHdF6IQAAAAAN0XohDhrOrc',
      // Real clients also send an Ed25519 third-party signature; the SDK requires the field.
      signature: 'ZGV2LW9ubHktc2lnbmF0dXJl',
      user: JSON.stringify({ id: userId, first_name: firstName, language_code: 'uz' }),
    },
    botToken ?? botTokenFromEnv(),
  )
  return new URLSearchParams({
    tgWebAppData: initData,
    tgWebAppVersion: '8.0',
    tgWebAppPlatform: 'tdesktop',
    tgWebAppThemeParams: JSON.stringify(theme),
  }).toString()
}
