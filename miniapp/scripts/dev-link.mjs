// Prints a URL that opens the Mini App in a normal browser as a signed-in Telegram user.
import { launchHash } from './launch-params.mjs'

const base = process.argv[2] ?? 'http://localhost:5173'
console.log(`${base}/#${launchHash({ firstName: 'Mirzohid' })}`)
