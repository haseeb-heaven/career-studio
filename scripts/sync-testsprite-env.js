#!/usr/bin/env node
/**
 * Reads FRONTEND_URL / FRONTEND_HOST / FRONTEND_PORT from the root .env
 * and updates testsprite_tests/tmp/config.json so TestSprite always uses
 * the correct local endpoint instead of a hardcoded URL.
 *
 * Usage:  node scripts/sync-testsprite-env.js
 */

const fs = require('fs')
const path = require('path')

const ROOT = path.join(__dirname, '..')
const ENV_FILE = path.join(ROOT, '.env')
const CONFIG_FILE = path.join(ROOT, 'testsprite_tests', 'tmp', 'config.json')

// Minimal .env parser (key=value, ignores comments and blank lines)
function parseEnv(filePath) {
  if (!fs.existsSync(filePath)) return {}
  const lines = fs.readFileSync(filePath, 'utf8').split('\n')
  const out = {}
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    const key = trimmed.slice(0, eq).trim()
    const val = trimmed.slice(eq + 1).trim().replace(/^["']|["']$/g, '')
    out[key] = val
  }
  return out
}

const env = parseEnv(ENV_FILE)

// Build the frontend URL from env vars
const frontendUrl =
  env.FRONTEND_URL ||
  `http://${env.FRONTEND_HOST || 'localhost'}:${env.FRONTEND_PORT || '5173'}`

if (!fs.existsSync(CONFIG_FILE)) {
  console.error(`Config file not found: ${CONFIG_FILE}`)
  process.exit(1)
}

const config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'))
const prev = config.localEndpoint

config.localEndpoint = frontendUrl

fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2))

if (prev !== frontendUrl) {
  console.log(`Updated TestSprite localEndpoint: ${prev} → ${frontendUrl}`)
} else {
  console.log(`TestSprite localEndpoint already correct: ${frontendUrl}`)
}
