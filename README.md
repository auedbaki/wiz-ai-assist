# 💡 WiZ AI Assist

> **Local Network UDP Control & Physical Ambient Status Lighting Protocol for AI Coding Assistants**

[![Python 3](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Protocol: UDP 38899](https://img.shields.io/badge/Protocol-UDP%2038899-orange.svg)](#architecture)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-0%20(Standard%20Lib)-success.svg)](#architecture)

**WiZ AI Assist** brings zero-cloud-latency local smart lighting control to Philips WiZ connected bulbs and introduces an **Ambient AI Status Signaling Protocol** that turns your desk lamp into a physical indicator for AI coding sessions (Antigravity, Claude Code, Cursor, Cline, etc.).

---

## 🌟 Key Features

- ⚡ **Zero Cloud Latency**: Communicates directly over local UDP port `38899`—no cloud latency, API keys, or developer accounts needed.
- 🚦 **Ambient AI Status Protocol**: Automatically reflects the AI assistant's state in physical room lighting:
  - 🔵 **Blue**: Agent is paused waiting for your confirmation, input, or question response.
  - 🔴 **Red**: An error, test failure, or exception occurred.
  - 🟢 **Green**: Task or goal successfully completed (stays green for 10s, then smoothly returns to warm white).
  - 🛋️ **Warm White (2700K)**: Default working light.
- 🎨 **Full RGB Color & Tunable White Support**: Supports 16M RGB colors (A60 color bulbs) and precision Kelvin tuning (2200K amber to 6500K cool daylight).
- 🚨 **High-Contrast Emergency Strobe Alert**: A fast, dramatic strobe alert that oscillates between 10% Warm Amber and 100% Cool Daylight White.
- 🔄 **Auto-Discovery & Dynamic MAC Recovery**: Automatically discovers WiZ bulbs on your local subnet and recovers dynamically if your router reassigns DHCP IPs.
- 🛡️ **Zero External Dependencies**: Built 100% on the Python 3 standard library (`socket`, `json`, `argparse`, `concurrent.futures`, `signal`).

---

## 🚦 Ambient AI Status Protocol

When working alongside an autonomous AI agent, you shouldn't have to keep staring at your terminal to know what's happening. WiZ AI Assist enables physical visual signaling:

| Event | Color | Command | Behavior |
| :--- | :--- | :--- | :--- |
| **Needs User Help / Confirmation** | 🔵 **Blue** | `wiz signal blue` | Glows blue while waiting for your decision; reverts to warm white once you reply |
| **Issue / Build Error / Test Failure** | 🔴 **Red** | `wiz signal red` | Glows red on failure; reverts to warm white once fixed |
| **Task Completed / Goal Met** | 🟢 **Green** | `wiz signal green` | Shines green for 10 seconds, then automatically returns to warm white |
| **Normal / Active Working State** | 🛋️ **Warm White** | `wiz signal warm` | Default 2700K cozy warm white (preserves your dimming level) |

> **Safety Guard**: The signal protocol inspects the lamp first. If the lamp is turned **OFF**, it will safely skip without turning the lamp on or disturbing your room.

---

## 🛠️ Supported Hardware

Tested and verified on:
- **Philips WiZ A60 RGBW Color Bulb** (`ESP25_SHRGB_01`, Firmware 1.38+)
- **Philips WiZ Tunable White T-Bulb** (`ESP25_SHTW_01`, Firmware 1.39+)
- **Philips WiZ Tunable White T-Bulb** (`ESP01_SHTW1C_31`, Firmware 1.35+)

### ⚠️ Firmware 1.39+ Security Note
Newer WiZ firmware releases introduce an *"Only verified controls"* security mode requiring HMAC-SHA256 signatures for local writes.
- **Easiest Fix (10 seconds)**: Open the WiZ mobile app $\rightarrow$ **Settings** $\rightarrow$ **Security** (under Current Home) $\rightarrow$ **Local communication** $\rightarrow$ Select **"All controls"**.

---

## 🚀 Quickstart & Installation

### 1. Clone the repository
```bash
git clone https://github.com/auedbaki/wiz-ai-assist.git
cd wiz-ai-assist
```

### 2. Link the CLI to your PATH
```bash
mkdir -p ~/.local/bin
ln -sf "$(pwd)/wiz_controller.py" ~/.local/bin/wiz
chmod +x wiz_controller.py
```
*(Ensure `~/.local/bin` is in your `$PATH`)*.

### 3. Discover Bulbs on Your Network
Run an automatic subnet discovery:
```bash
wiz scan
```

### 4. Create your Configuration
Copy the template configuration:
```bash
mkdir -p ~/.agents/skills/wiz-bulb
cp config.example.json ~/.agents/skills/wiz-bulb/config.json
```
Edit `~/.agents/skills/wiz-bulb/config.json` with your discovered IP addresses and bulb names.

---

## 💻 CLI Usage Guide

### Check Bulb Status
```bash
wiz status                 # Status of all bulbs
wiz lamp status            # Status of the A60 lamp
wiz t bulb status          # Status of the ceiling T-bulb
```

### Ambient AI Status Signals
```bash
wiz signal blue            # Waiting for user input / confirmation
wiz signal red             # Error or failure occurred
wiz signal green           # Task successfully completed (auto-reverts in 10s)
wiz signal warm            # Restore default warm white
```

### Controlling the Lamp (A60 RGBW Color)
```bash
wiz lamp on
wiz lamp off
wiz lamp toggle
wiz lamp dim 60            # Brightness 10% to 100%

# Vibrant Colors:
wiz lamp red
wiz lamp blue
wiz lamp green
wiz lamp purple
wiz lamp cyan
wiz lamp orange
wiz lamp yellow
wiz lamp pink
wiz lamp color 255 100 0   # Custom RGB values

# Tunable Whites:
wiz lamp warm              # 2700K Warm White
wiz lamp cool              # 6500K Daylight Cool White
wiz lamp neutral           # 4000K Neutral White
wiz lamp reading           # 4200K Ergonomic Reading Light (100%)
wiz lamp cozy              # Scene 6 Cozy Mode
```

### Controlling Ceiling T-Bulb
```bash
wiz t bulb on
wiz t bulb off
wiz t bulb warm
wiz t bulb cool
wiz t bulb dim 80
```

### High-Contrast Strobe Alert
```bash
wiz alert                  # 6-cycle fast strobe (10% Warm <-> 100% Cool)
wiz alert -c 10            # 10 cycles
wiz alert start            # Continuous strobe loop in background
wiz alert stop             # Stop alert and restore cool white
```

### Multi-Bulb Grouping
```bash
wiz myroom on              # Turn on all room lights together
wiz myroom off             # Turn off all room lights together
wiz all off                # Turn off all lights in the house
```

---

## 🤖 AI Agent Integration

To equip your AI assistant (Google Antigravity, Claude Code, Cursor, Cline, etc.) with automatic smart lighting signals, add this to your project's `AGENTS.md` or system prompt:

```markdown
# Ambient Status Lighting Protocol
Yash has an A60 WiZ RGBW bulb in his room lamp (`wiz signal <type>`).
1. Only signal if the Lamp is already ON (handled safely by CLI).
2. Needs Confirmation / Input: Run `wiz signal blue`. Revert to `wiz signal warm` when user replies.
3. Issue / Error: Run `wiz signal red`. Revert to `wiz signal warm` when resolved.
4. Success / Completed: Run `wiz signal green` (stays green for 10s, then reverts to warm automatically).
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
