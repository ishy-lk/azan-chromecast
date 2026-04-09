// RadioWidget.js — Scriptable widget to control radio on Chromecast
// Add as a medium widget on your home screen

const CONFIG = {
  piUrl:      "http://192.168.1.200:8000",
  radioUrl:   "https://radio.lotustechnologieslk.net:8006/;stream.mp3",
  radioName:  "Lotus FM",
  scriptName: "RadioWidget",   // must match the script name in Scriptable
}

// ── Action mode (triggered by widget tap via scriptable:// URL) ──────────────
const action = args.queryParameters.action
if (action === "play" || action === "stop") {
  const endpoint = action === "play"
    ? `/api/play?url=${encodeURIComponent(CONFIG.radioUrl)}`
    : `/api/stop`
  try {
    const req = new Request(`${CONFIG.piUrl}${endpoint}`)
    const resp = await req.loadJSON()
    console.log(`[RadioWidget] ${action} → ${JSON.stringify(resp)}`)
  } catch (e) {
    console.error("[RadioWidget] Failed to reach Pi:", e.message)
  }
  Script.complete()
  return
}

// ── Widget UI ────────────────────────────────────────────────────────────────
const w = new ListWidget()
w.backgroundColor = new Color("#0f1923")
w.setPadding(14, 14, 14, 14)

// Header
const header = w.addStack()
header.layoutHorizontally()
header.centerAlignContent()
const icon = header.addText("📻")
icon.font = Font.systemFont(24)
header.addSpacer(8)
const titleText = header.addText(CONFIG.radioName)
titleText.font = Font.boldSystemFont(15)
titleText.textColor = Color.white()
titleText.lineLimit = 1

w.addSpacer()

// Buttons row
const row = w.addStack()
row.layoutHorizontally()
row.spacing = 10

// Play button
const playBtn = row.addStack()
playBtn.backgroundColor = new Color("#1db954")
playBtn.cornerRadius = 10
playBtn.setPadding(10, 20, 10, 20)
playBtn.url = `scriptable:///run?scriptName=${CONFIG.scriptName}&action=play`
const playLabel = playBtn.addText("▶  Play")
playLabel.font = Font.boldSystemFont(14)
playLabel.textColor = Color.white()

row.addSpacer()

// Stop button
const stopBtn = row.addStack()
stopBtn.backgroundColor = new Color("#c0392b")
stopBtn.cornerRadius = 10
stopBtn.setPadding(10, 20, 10, 20)
stopBtn.url = `scriptable:///run?scriptName=${CONFIG.scriptName}&action=stop`
const stopLabel = stopBtn.addText("⏹  Stop")
stopLabel.font = Font.boldSystemFont(14)
stopLabel.textColor = Color.white()

Script.setWidget(w)

if (config.runsInApp) {
  await w.presentMedium()
}

Script.complete()
