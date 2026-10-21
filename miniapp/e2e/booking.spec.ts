import { expect, test, type Page } from '@playwright/test'

import { launchHash } from '../scripts/launch-params.mjs'

/** Open the Mini App as a fresh Telegram user (signed initData, like the real client). */
async function openAsNewUser(page: Page, path = '/') {
  const userId = 700_000_000 + Math.floor(Math.random() * 99_999_999)
  await page.goto(`${path}#${launchHash({ userId, firstName: 'E2E' })}`)
}

test('opening outside Telegram explains how to launch the app', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Telegram orqali oching')).toBeVisible()
})

test('customer books, confirms and cancels an appointment', async ({ page }) => {
  await openAsNewUser(page)
  await expect(page.getByRole('heading', { name: 'Nur Klinika' })).toBeVisible()
  await expect(page.getByText('Assalomu alaykum, E2E!')).toBeVisible()

  // Catalog
  await page.getByTestId('home-services').first().click()
  const dental = page.getByTestId('service-card').filter({ hasText: 'Stomatolog qabuli' })
  await expect(dental).toContainText("150 000 so'm")
  await dental.click()

  // Find the first day with free slots and pick the first time
  await expect(page.getByRole('heading', { name: 'Stomatolog qabuli' })).toBeVisible()
  const days = page.getByTestId('day-picker').getByRole('button')
  for (let i = 0; i < (await days.count()); i++) {
    await days.nth(i).click()
    const outcome = page.getByTestId('slots').or(page.getByTestId('empty-state'))
    await expect(outcome).toBeVisible()
    if (await page.getByTestId('slots').isVisible()) break
  }
  const slot = page.getByTestId('slot').first()
  const time = (await slot.textContent())!.trim()
  await slot.click()
  await expect(page.getByTestId('main-button')).toHaveText(`Davom etish · ${time}`)
  await page.getByTestId('main-button').click()

  // Pending booking -> confirm
  await expect(page.getByRole('heading', { name: 'Qabulni tasdiqlang' })).toBeVisible()
  await expect(page.getByTestId('booking-summary')).toContainText(time)
  await expect(page.getByTestId('booking-summary')).toContainText('Tasdiqlanmagan')
  await page.getByTestId('main-button').click()
  await expect(page.getByRole('heading', { name: /Qabul tasdiqlandi/ })).toBeVisible()
  await expect(page.getByTestId('booking-summary')).toContainText('Tasdiqlangan')

  // My bookings -> cancel (also frees the slot for the next run)
  await page.getByTestId('main-button').click()
  const card = page.getByTestId('upcoming').getByTestId('booking-card')
  await expect(card).toHaveCount(1)
  await expect(card).toContainText('Stomatolog qabuli')
  await card.getByTestId('cancel-booking').click()
  await card.getByTestId('confirm-cancel').click()
  await expect(page.getByTestId('history').getByTestId('booking-card')).toContainText(
    'Bekor qilingan',
  )
})

test('a slot taken by someone else cannot be booked twice', async ({ browser }) => {
  const a = await browser.newPage()
  const b = await browser.newPage()
  for (const page of [a, b]) {
    await openAsNewUser(page)
    await page.getByTestId('home-services').first().click()
    await page.getByTestId('service-card').filter({ hasText: 'Kardiolog qabuli' }).click()
    await page.getByTestId('day-picker').getByRole('button').nth(1).click() // tomorrow
    await page.getByTestId('slot').last().click()
  }
  await a.getByTestId('main-button').click()
  await expect(a.getByRole('heading', { name: 'Qabulni tasdiqlang' })).toBeVisible()

  await b.getByTestId('main-button').click()
  await expect(b.getByRole('alert')).toContainText('hozirgina band qilindi')
  await expect(b).toHaveURL(/\/book\//)
})
