export const TIME_ZONE = 'Asia/Tashkent'

const WEEKDAYS = ['Ya', 'Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh']
const MONTHS = [
  'yanvar',
  'fevral',
  'mart',
  'aprel',
  'may',
  'iyun',
  'iyul',
  'avgust',
  'sentabr',
  'oktabr',
  'noyabr',
  'dekabr',
]

/** 150000 -> "150 000 so'm" */
export function formatPrice(uzs: number): string {
  return `${uzs.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')} so'm`
}

function parts(date: Date): { year: number; month: number; day: number; weekday: number } {
  const p = new Intl.DateTimeFormat('en-US', {
    timeZone: TIME_ZONE,
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    weekday: 'short',
  }).formatToParts(date)
  const get = (type: string) => p.find((x) => x.type === type)?.value ?? ''
  const weekday = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(get('weekday'))
  return { year: +get('year'), month: +get('month'), day: +get('day'), weekday }
}

/** "YYYY-MM-DD" in the clinic's time zone. */
export function isoDate(date: Date): string {
  const { year, month, day } = parts(date)
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

export function formatTime(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: TIME_ZONE,
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).format(new Date(iso))
}

/** "Payshanba, 23-oktabr" style label for a timestamp. */
export function formatDay(iso: string): string {
  const full = ['Yakshanba', 'Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba']
  const { month, day, weekday } = parts(new Date(iso))
  return `${full[weekday]}, ${day}-${MONTHS[month - 1]}`
}

export function formatDateTime(iso: string): string {
  return `${formatDay(iso)}, ${formatTime(iso)}`
}

export interface DayOption {
  iso: string
  weekday: string
  day: number
}

/** The next `count` days starting today (clinic time zone). */
export function nextDays(count: number, from: Date = new Date()): DayOption[] {
  return Array.from({ length: count }, (_, i) => {
    const date = new Date(from.getTime() + i * 86_400_000)
    const { day, weekday } = parts(date)
    return { iso: isoDate(date), weekday: i === 0 ? 'Bugun' : WEEKDAYS[weekday], day }
  })
}

/** Whole minutes until `iso`; 0 once it has passed, at least 1 while time remains. */
export function minutesLeft(iso: string, now: number = Date.now()): number {
  const ms = new Date(iso).getTime() - now
  return ms <= 0 ? 0 : Math.max(1, Math.floor(ms / 60_000))
}
