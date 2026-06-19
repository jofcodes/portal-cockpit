# Portal Productivity Cockpit

A glanceable productivity hub for your **Meta Portal**. It reuses the same
pattern as Jo's separate **beehive-monitor** project (the `bee` repo) — but is
its own standalone project: local Python jobs gather signals from your work
tools, a **local Llama model** summarizes/drafts, results are written as JSON,
and a self-contained dashboard renders them on the Portal.

**Guardrails:** anything outbound (email replies, posts) is staged as a **draft**
for one-tap approval — never auto-sent. The LLM is **local-only** (Ollama on
`127.0.0.1`). Personal data stays on your machine/LAN and is **git-ignored**.

```
work tools ──(meta CLI)──► cockpit/jobs/*  ──► portal_data/*.json
                                  │  (local Llama summarizes/drafts)
                                  ▼
                       cockpit/build_cockpit.py ──► one self-contained HTML page
                                  ▼
              cockpit/server.py  (Mac "brain", 0.0.0.0:8899)
                                  ▼
                  Portal browser → http://<mac-lan-ip>:8899/
```

## Tabs
| Tab | Shows | Jobs |
|-----|-------|------|
| **Now / Next** | morning headline, next meeting, **meeting-prep packet**, today's focus, agenda, shared docs, **extracted action items** | A1 + A3 + A10 |
| **Inbox** | priority unread, drafted replies, waiting-on + draft nudges | A2 + A5 |
| **Workplace** | **action notifications** (with tab badge), **weekly digest**, Monday "Top of Mind" draft | A8 + A6 + Top of Mind |
| **Wrap** | end-of-day recap + tomorrow preview | A7 |

## What's built
- `cockpit/` — Python package: `config`, `llm` (local Llama), `connectors`
  (`meta google.*`), `sample_data`, `build_cockpit` (4-tab dashboard),
  `server` (Flask brain), and `jobs/`:
  - `brief` (A1), `inbox` (A2+A5), `meeting_prep` (A3), `wrap` (A7)
  - `top_of_mind` (Mon), `workplace_digest` (A6), `notifications` (A8), `doc_actions` (A10)
- `cockpit_app/` — a **native Portal app** (`com.josephine.cockpit`), installed
  and running on the Portal. Built **without Gradle** via `build_apk.sh`
  (plain Java, no deps → aapt2/javac/d8/zipalign/apksigner). `./deploy.sh`
  builds + installs + launches; `./refresh.sh` hot-updates the dashboard.
- `scripts/cockpit_job.sh` + launchd plists — 8am brief+inbox+meeting-prep+notifs,
  5pm wrap+notifs, Fri 4pm digest, Mon 8am Top of Mind, plus an always-on server.

> **Note on A6/A8:** there's no clean first-party Workplace CLI yet, so
> `connectors.workplace_*` are stubs that fall back to sample data. The jobs and
> UI are complete — wire those connectors to the real Workplace surface to go live.

## Run it

### 1. One-time: authenticate the connectors (for real data)
The jobs read Gmail/Calendar/Drive via the `meta` CLI, which needs Google
Workspace OAuth. Until you do this, jobs use **sample data** (badged "SAMPLE").

```bash
# Visit https://www.internalfb.com/intern/jf/authenticate/ then:
jf auth --skip-legacy-auth-upgrade <UID> <NONCE>
# Verify:
meta google.gmail.message profile
```

### 2. Generate data + dashboard
```bash
cd "/Users/j0sephine/Documents/AI outputs/portal-cockpit"
.venv/bin/python -m cockpit.jobs.brief        # A1
.venv/bin/python -m cockpit.jobs.inbox        # A2+A5 (creates Gmail DRAFTS when authed)
.venv/bin/python -m cockpit.jobs.wrap         # A7
.venv/bin/python -m cockpit.jobs.top_of_mind  # Monday post draft
.venv/bin/python -m cockpit.build_cockpit     # render the dashboard
```

### 3. Show it on the Portal (HTTP — works today, no APK)
```bash
.venv/bin/python -m cockpit.server            # serves on http://<lan-ip>:8899/
# Point the Portal browser at it:
/usr/local/platform-tools/adb shell am start -n org.chromium.chrome/com.google.android.apps.chrome.Main \
  -a android.intent.action.VIEW -d "http://<mac-lan-ip>:8899/"
```
The server re-renders on every load, so scheduled jobs show up automatically.

### 4. (Optional) Native app — nicer, no browser chrome
The native app needs an APK build. **This must be run in your own Terminal**
(the assistant's sandbox blocks Gradle's daemon socket):
```bash
cd cockpit_app && ./deploy.sh     # builds APK, installs + launches "Cockpit" on the Portal
```
`deploy.sh` auto-detects Android Studio's bundled JDK and your Android SDK.

## Schedule it (launchd)
```bash
cp com.josephine.cockpit.server.plist ~/Library/LaunchAgents/
cp scripts/com.josephine.cockpit.{morning,eod,monday}.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.josephine.cockpit.*.plist
launchctl list | grep cockpit
```

## Model
Local Ollama on `127.0.0.1:11434`, model `llama3.1:8b` (text). Override with
`COCKPIT_MODEL`. (`llama3.2-vision` is currently broken in this Ollama build —
`mllama` arch unsupported — so text uses `llama3.1:8b`.)

## Still to do (later phases, per the brief)
The voice layer (whisper.cpp + Piper); Home/Bee toggle; wiring the real
Workplace connector for A6/A8. **Top of Mind** needs your real group + 2-3
example posts: set `COCKPIT_TOM_GROUP` and put examples in
`cockpit/voice_examples.txt` (one per `---` separator).
```
