# macOS Distribution

Build and distribute 42-Training as a native macOS `.app` / `.dmg`.

## Architecture

The desktop build bundles three services into a single Electron application:

```
42-Training.app/
  Contents/
    MacOS/
      42-Training          ← Electron binary
    Resources/
      backend/
        api/               ← Python API + virtualenv (SQLite mode)
        ai_gateway/        ← Python AI Gateway + virtualenv
      frontend/            ← Next.js standalone build
      data/                ← Curriculum JSON + progression
```

On launch the Electron main process spawns:

1. **API backend** (port 8000) — FastAPI with SQLite instead of PostgreSQL
2. **AI Gateway** (port 8100) — FastAPI, connects to the local API
3. **Next.js frontend** (port 3000) — standalone server

The BrowserWindow opens `http://127.0.0.1:3000` once all health checks pass.

### Local vs. server mode

| Aspect | Desktop (this build) | Server (docker-compose) |
|---|---|---|
| Database | SQLite in `~/Library/Application Support/42-Training/` | PostgreSQL 16 |
| Cache | In-memory (no Redis) | Redis 7 |
| Auth | Local JWT with static key | JWT with configurable secret |
| LLM | Optional — rule-based fallback | Anthropic API |

## Prerequisites

| Requirement | Version | Check |
|---|---|---|
| macOS | 13 Ventura+ | `sw_vers` |
| Xcode CLI Tools | Latest | `xcode-select -p` |
| Node.js | 20+ | `node --version` |
| Python | 3.13+ | `python3 --version` |
| npm | 10+ | `npm --version` |

Install prerequisites:

```bash
# Xcode Command Line Tools
xcode-select --install

# Node.js (via Homebrew)
brew install node@20

# Python 3.13
brew install python@3.13
```

## Build

### Unsigned build (development)

```bash
./scripts/build-macos.sh
```

This produces `desktop/dist/42-Training-1.0.0-universal.dmg` without code signing.
macOS Gatekeeper will block unsigned apps — right-click > Open to bypass during development.

### Signed + notarized build (distribution)

```bash
export APPLE_ID="developer@example.com"
export APPLE_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export APPLE_TEAM_ID="XXXXXXXXXX"
export CSC_NAME="Developer ID Application: Your Name (XXXXXXXXXX)"

./scripts/build-macos.sh --sign
```

## Code Signing

### Requirements

1. **Apple Developer Program** membership ($99/year)
2. **Developer ID Application** certificate installed in Keychain
3. **App-specific password** generated at [appleid.apple.com](https://appleid.apple.com/account/manage)

### Certificates

Generate via Xcode or Apple Developer portal:

```
Keychain Access → Certificate Assistant → Request a Certificate from a CA
```

Then download and install the **Developer ID Application** certificate.

Verify it is installed:

```bash
security find-identity -v -p codesigning
```

You should see a line like:

```
1) ABCDEF1234 "Developer ID Application: Your Name (TEAMID)"
```

### Environment variables

| Variable | Description |
|---|---|
| `CSC_NAME` | Full name of the signing certificate (from `security find-identity`) |
| `APPLE_ID` | Apple Developer account email |
| `APPLE_APP_PASSWORD` | App-specific password for notarization |
| `APPLE_TEAM_ID` | 10-character Team ID from developer portal |

### Entitlements

The app requires these macOS entitlements (configured in `desktop/build/entitlements.mac.plist`):

| Entitlement | Why |
|---|---|
| `cs.allow-unsigned-executable-memory` | Electron requires this for V8 JIT |
| `network.client` + `network.server` | Local loopback communication between services |
| `cs.allow-jit` | Spawn Python and Node child processes |
| `files.user-selected.read-write` | SQLite database in Application Support |

### Notarization

Notarization happens automatically during `--sign` builds via the `desktop/scripts/notarize.js` afterSign hook. The process:

1. `electron-builder` signs the `.app` with your Developer ID certificate
2. The afterSign hook submits the `.app` to Apple's notarization service
3. Apple scans for malware and validates entitlements
4. The notarization ticket is stapled to the `.app`

Notarization typically takes 2-10 minutes. If it fails, check:

```bash
xcrun notarytool log <submission-id> --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID"
```

## Configuration

### LLM API keys

The AI Gateway works without API keys — it falls back to rule-based scoring.
To enable Claude-powered features, set environment variables before launching:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
open /Applications/42-Training.app
```

Or create `~/Library/Application Support/42-Training/.env` with:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### Data location

All persistent data is stored in:

```
~/Library/Application Support/42-Training/
├── 42training.db        ← SQLite database
└── .env                 ← Optional environment overrides
```

## Troubleshooting

### App fails to start

Check logs in Console.app — filter by `42-Training`. Common issues:

- **Port conflict**: Another process is using 8000, 8100, or 3000
- **Python not found**: The build bakes in a virtualenv — if you moved the .app, paths break
- **Gatekeeper block**: Right-click > Open on first launch (unsigned builds)

### Database reset

Delete the SQLite database to start fresh:

```bash
rm ~/Library/Application\ Support/42-Training/42training.db
```

### Rebuild from scratch

```bash
rm -rf desktop/dist desktop/backend desktop/frontend desktop/data desktop/node_modules
./scripts/build-macos.sh
```

## CI/CD

For automated builds in GitHub Actions, add a macOS runner job:

```yaml
jobs:
  build-macos:
    runs-on: macos-14
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.13" }
      - run: ./scripts/build-macos.sh --sign
        env:
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_APP_PASSWORD: ${{ secrets.APPLE_APP_PASSWORD }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
          CSC_LINK: ${{ secrets.CSC_LINK }}
          CSC_KEY_PASSWORD: ${{ secrets.CSC_KEY_PASSWORD }}
      - uses: actions/upload-artifact@v4
        with:
          name: 42-Training.dmg
          path: desktop/dist/*.dmg
```

`CSC_LINK` is a base64-encoded `.p12` certificate file. `CSC_KEY_PASSWORD` is its passphrase.
