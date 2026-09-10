#!/usr/bin/env node
/**
 * ShopDesk-Launcher: startet Dev-Server, Build oder Preview mit fest eingebrannten Bug-Flags.
 *
 *   npm run dev -- --bug=coupon-noop
 *   npm run dev -- --bug=coupon-noop,qty-stale-total,flaky-race     # mehrere Bugs in einer Instanz
 *   npm run dev -- --bug=double-submit --port=5174
 *   npm run build -- --bug=coupon-noop --out-dir=dist-coupon-noop
 *   npm run preview -- --out-dir=dist-coupon-noop --port=4174
 *
 * Ohne --bug läuft die fehlerfreie Version. Die Flags landen über `define` in
 * `import.meta.env.VITE_BUG` und lassen sich zur Laufzeit nicht über die URL ändern.
 */
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseArgs } from 'node:util'
import { build, createServer, preview } from 'vite'
import catalog from '../src/bugs/catalog.json' with { type: 'json' }

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const COMMANDS = ['dev', 'build', 'preview']
const ACTIVE_FLAGS = Object.keys(catalog)
const FLAGS = ['none', ...ACTIVE_FLAGS]

const USAGE = `ShopDesk launcher

Usage:
  node scripts/shopdesk.mjs <dev|build|preview> [--bug=<flag>[,<flag>...]] [--port=<n>] [--host=<host>] [--out-dir=<dir>] [--open]

--bug takes one or more flags (comma-separated or repeated). Without --bug everything works.

Via npm (note the double dash before the options):
  npm run dev -- --bug=coupon-noop
  npm run dev -- --bug=coupon-noop,qty-stale-total,flaky-race
  npm run dev -- --bug=double-submit --port=5174
  npm run build -- --bug=coupon-noop --out-dir=dist-coupon-noop
  npm run preview -- --out-dir=dist-coupon-noop --port=4174

Bug flags:
  ${FLAGS.join(', ')}
`

function fail(message) {
  console.error(`\n  x ${message}\n`)
  console.error(USAGE)
  process.exit(1)
}

function parseCli(args) {
  try {
    return parseArgs({
      args,
      allowPositionals: true,
      options: {
        bug: { type: 'string', multiple: true },
        port: { type: 'string' },
        host: { type: 'string' },
        'out-dir': { type: 'string' },
        open: { type: 'boolean' },
        help: { type: 'boolean', short: 'h' },
      },
    })
  } catch (error) {
    return fail(error instanceof Error ? error.message : String(error))
  }
}

function parsePort(raw) {
  if (raw === undefined) return undefined
  const port = Number(raw)
  if (!Number.isInteger(port) || port < 1 || port > 65535) fail(`Invalid port "${raw}".`)
  return port
}

function resolveBugs(rawValues) {
  const requested = rawValues
    .flatMap((value) => value.split(/[\s,]+/))
    .map((value) => value.trim().toLowerCase())
    .filter((value) => value !== '')
  const unknown = requested.filter((flag) => !FLAGS.includes(flag))
  if (unknown.length > 0) fail(`Unknown bug flag${unknown.length > 1 ? 's' : ''}: ${unknown.join(', ')}.`)
  const bugs = [...new Set(requested.filter((flag) => flag !== 'none'))]
  if (requested.includes('none') && bugs.length > 0) fail('"none" cannot be combined with other bug flags.')
  return bugs.sort((a, b) => ACTIVE_FLAGS.indexOf(a) - ACTIVE_FLAGS.indexOf(b))
}

function describe(bugs) {
  if (bugs.length === 0) return 'ShopDesk mode: none (everything works)'
  const lines = bugs.map((bug) => `    - ${bug}: ${catalog[bug].symptom}`)
  return `ShopDesk mode: ${bugs.length} bug${bugs.length > 1 ? 's' : ''} active\n${lines.join('\n')}`
}

const { values, positionals } = parseCli(process.argv.slice(2))
if (values.help) {
  console.log(USAGE)
  process.exit(0)
}

const command = positionals[0] ?? 'dev'
if (!COMMANDS.includes(command)) fail(`Unknown command "${command}". Expected one of: ${COMMANDS.join(', ')}.`)
if (positionals.length > 1) fail(`Unexpected argument "${positionals[1]}".`)
if (command === 'preview' && values.bug !== undefined) {
  fail('"preview" serves an existing build as it was built – pass --bug to "build" instead.')
}

const bugs = resolveBugs(values.bug ?? [])
const port = parsePort(values.port)
const outDir = values['out-dir']
const define = { 'import.meta.env.VITE_BUG': JSON.stringify(bugs.join(',')) }
const banner = describe(bugs)

if (command === 'dev') {
  const server = await createServer({
    root: ROOT,
    define,
    server: { port, host: values.host, open: values.open },
  })
  await server.listen()
  server.config.logger.info(`\n  ${banner}\n`)
  server.printUrls()
  server.bindCLIShortcuts({ print: true })
} else if (command === 'build') {
  console.log(`\n  ${banner}\n`)
  await build({ root: ROOT, define, build: { outDir } })
} else {
  const server = await preview({
    root: ROOT,
    build: { outDir },
    preview: { port, host: values.host, open: values.open },
  })
  server.printUrls()
  server.bindCLIShortcuts({ print: true })
}
