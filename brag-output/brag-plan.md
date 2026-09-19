# Brag Plan: jev-mail-classifier

## What is this app?
A terminal tool that connects to your real IMAP inbox and classifies every unread email against plain-language categories using Jev (TypeSafe's yes/no probability model) — one API call per email, no prompt engineering, no JSON parsing, then auto-tags/moves/flags/notifies, all from a keyboard-only Textual TUI.

## The angle
Play it as a terminal speed-flex: the product's own tagline is "Your inbox, judged in milliseconds" — so the video *is* that claim, sped up and slammed onto screen. Chaotic energy comes from the real mechanics: a wall of unread mail, one command, then tags/moves/flags detonating onto messages in rapid fire. The comedy isn't invented — it's the actual "no LLM prompt engineering, no per-email API bill that adds up" swagger from the README, delivered at full volume.

## Hook (first 2-3 seconds)
Black terminal. Cursor blinks. The ASCII "JEV MAIL" logo from the README glitches/scan-lines into frame, then the line types out fast: `YOUR INBOX. JUDGED IN MILLISECONDS.`

## Key moments (the middle)
- A cluttered unread inbox list rips down the screen, unread counter ticking up chaotically (482 UNREAD).
- `$ jev-mail run` typed at a prompt; one email row locks in, an arrow fires to a small "JEV" box, and per-category probabilities snap in as numbers (invoice 0.94, urgent 0.81, spam 0.02) — the actual multi-label-yes/no mechanic from the README diagram.
- Actions detonate onto the email row one by one, hard-cut per hit: `TAG: Invoice` → `MOVE: Invoices/` → `FLAG ⚑` — real action types from the actions table.
- Rapid-fire ALL-CAPS claim dump, one per beat: `ONE API CALL.` / `NO JSON PARSING.` / `A FRACTION OF A CENT.`

## Outro / punchline
Cluttered inbox column crash-cuts into three sorted folders (Invoices, Urgent, Spam) with counts, emails snapping into place — then the ASCII logo slams full screen with the tagline and the project name. Cut to black.

## User flow worth showing
Entry → key action → result, pulled straight from the real CLI/TUI, not marketing copy:
1. **Entry:** a messy unread inbox (`jev-mail run` about to fire against real unprocessed mail).
2. **Key action:** each email goes through Jev — one call, per-category probabilities returned, threshold checked, matching actions fired (tag/move/flag/webhook).
3. **Result:** inbox is sorted into folders with `$JevProcessed` quietly marking what's done — no dashboard, no separate database, just a clean mailbox.

## Tone
- Preset: chaotic
- Creative direction: terminal hacker flex — ANSI colors, hard cuts, ASCII glitch text, emails detonating into folders in real time
- Interpretation: 6-8 short scenes, none over 3s, hard cuts and flash cuts between beats, ALL CAPS stat dumps, but every readable line still gets its floor hold (see Reading time) so the speed reads as edited, not illegible

## Format: landscape — 1920x1080
## Duration: ~19s

## Visual identity (from the project)
- Background: near-black terminal (`#0d1117`-class dark, matches Textual's default dark theme — no literal CSS in this project since it's a TUI, not a web app)
- Accent: purple `#8A2BE2`-class (from the README's "Powered by Jev" badge) plus terminal green `#39FF88`-class for success/tag states and a warning amber for flags
- Text: off-white/light gray terminal foreground, high contrast on black
- Display font: monospace (e.g. JetBrains Mono / Fira Code) — the ASCII banner and all on-screen text should read as genuine terminal output
- Body font: same monospace family — this is a terminal product, there is no separate display/body split
- Strongest visual element: the README's ASCII "JEV MAIL" block logo, and the IMAP → Jev → mailbox arrow diagram (real, from the README's "How it works" section)

## Share copy (draft)
Built a CLI that reads your inbox and judges it in milliseconds — no prompts, no JSON, no per-email bill. jev-mail-classifier, open source.

## Audio direction
- Role: dense rhythmic layer, terminal-native (keyboard clacks, hard hits) over a driving synth/electronic bed
- Music: fast, aggressive electronic/synth bed (~120-140 BPM feel) — mood over specific track; Hyperframes selects from bundled library
- Music treatment: cold open on the hook (no pre-roll), bed enters within the first beat, hard cuts land on downbeats, brief drop/silence right before the outro slam, then a final hit on the logo
- Music cue guidance: to be detected at composition time (`npx hyperframes beats` or `analyze_music_cues.py`); target strong cues at (a) the hook logo glitch-in, (b) the first action-detonation hit (`TAG: Invoice`), (c) the outro logo slam. Sequential reveals (probabilities snapping in, action stamps) should land on alternating beats, not every beat, so each stays readable.
- Audio-reactive treatment: subtle — scan-line/glitch intensity on the hook logo and a faint terminal-glow pulse on the action stamps may track music energy; no waveform bars, nothing literal
- SFX posture: moderate-to-dense but motion-matched, never random — mechanical keystrokes for typed lines, a sharp stamp/hit per action detonation, a soft chime per folder-sort snap, one dry logo hit on the outro
- Audio-coupled moments: the hook line types out with key ticks; each probability number "snaps" in with a short tick; each action (TAG/MOVE/FLAG) gets its own stamp hit; folder counts increment with a tally tick
- Restraint rule: never let SFX density outrun what's legible on screen — a beat can carry a stamp/tick even when it can't carry a new full line of text

## Storyboard

### Scene 1 — Hook — 2.5s
Black terminal, cursor blinking. The README's ASCII "JEV MAIL" block logo glitches/scan-lines into frame, then `YOUR INBOX. JUDGED IN MILLISECONDS.` types out character by character beneath it.
Sequential/interaction: yes — logo glitch-resolves in two quick flickers, then the line types out left to right.
Audio intent: cold-open jolt — the video announces itself instantly, no soft build.
Audio-coupled idea: key-tick sounds synced to each typed character.
Music: bed enters on the first glitch flicker, full energy immediately.
Transition mood: flash → Scene 2

### Scene 2 — The mess — 2s
A wall of unread email rows rips downward fast (real-looking subjects: invoices, newsletters, urgent client asks, spam). A counter in the corner ticks up chaotically: `482 UNREAD`.
Sequential/interaction: yes — rows stream past at speed, counter increments rapidly.
Audio intent: rising noise/clutter — sets up the relief of the next scene.
Audio-coupled idea: rapid tally-tick under the counter.
Transition mood: hard cut → Scene 3

### Scene 3 — The command — 2.5s
Prompt line: `$ jev-mail run` types out, executes. One email row locks into focus, an arrow fires from the row to a small labeled box `JEV`, and per-category probabilities snap in one by one: `invoice 0.94` / `urgent 0.81` / `spam 0.02` — mirroring the README's real IMAP → Jev → mailbox diagram.
Sequential/interaction: yes — command types, then the three probability values snap in one at a time, alternating-beat spaced so each is readable.
Audio intent: mechanical precision — the "one call, one answer" moment.
Audio-coupled idea: key ticks on the command; a distinct snap/tick per probability value landing.
Transition mood: hard cut → Scene 4

### Scene 4 — Detonation — 3s
The same email row takes hits one at a time, each a hard-cut stamp: `TAG: Invoice` → `MOVE: Invoices/` → `FLAG ⚑`. Each stamp fills more of the frame than the last.
Sequential/interaction: yes — three action stamps land in sequence, each on its own beat, each held to its reading floor (~0.8s) before the next.
Audio intent: aggressive, satisfying impact — the payoff of the setup in Scene 3.
Audio-coupled idea: a sharp stamp/hit sound per action landing.
Transition mood: flash cut → Scene 5

### Scene 5 — Claim dump — 2.5s
Rapid-fire ALL CAPS lines replace each other: `ONE API CALL.` / `NO JSON PARSING.` / `A FRACTION OF A CENT.` — each is a real claim from the README, not invented copy.
Sequential/interaction: yes — one line replaces the previous at speed, each still held to its reading floor.
Audio intent: hype crescendo building toward the result.
Audio-coupled idea: a hard hit under each line's arrival.
Transition mood: zoom cut → Scene 6

### Scene 6 — Sorted — 3s
Split screen: the chaotic inbox column from Scene 2 crash-cuts into three clean folder columns — `Invoices`, `Urgent`, `Spam` — each with a count, emails snapping into their column one by one.
Sequential/interaction: yes — emails snap into their target folder column in quick succession, counts increment as they land.
Audio intent: release — the chaos resolves into order.
Audio-coupled idea: a soft chime per email-to-folder snap; brief near-silence just before, for contrast.
Transition mood: hard cut → Scene 7

### Scene 7 — Outro — 3.5s
The ASCII "JEV MAIL" logo slams full-screen, centered. Beneath it: `YOUR INBOX. JUDGED IN MILLISECONDS.` then, smaller, `jev-mail-classifier`. Hold, then cut to black.
Sequential/interaction: none — single slam-in, then a settled hold.
Audio intent: final statement — confident, then silence.
Audio-coupled idea: one dry logo-hit on the slam-in, then the music drops out under the hold.
Transition mood: hard cut → black (end)

**Music mood for this video:** chaotic
**Audio summary:** A driving, aggressive electronic bed enters cold on the hook and never softens until the sorted-inbox release in Scene 6, punctuated throughout by motion-matched keystrokes, stamps, and snaps; it drops out under the final logo hold so the last beat lands in near-silence.
