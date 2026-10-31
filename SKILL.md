---
name: wiz-ai-assist
description: >-
  Control Philips WiZ Smart Bulbs locally over Wi-Fi and provide ambient physical status lighting for AI coding agents.
  Features instant local UDP control (on/off, brightness, Kelvin color temp, RGB colors, dynamic scenes, fast strobe alerts)
  and ambient AI lifecycle signaling (Blue for user input/confirmation, Red for errors, Green for task completion).
---

# WiZ AI Assist - Smart Bulb Controller & Ambient AI Lighting Skill

Provides local UDP network control for Philips WiZ Connected smart bulbs on port 38899 without requiring cloud APIs, and integrates physical ambient status lighting for AI pair programming sessions.

## Features
- **Zero Cloud Latency**: Direct UDP JSON-RPC control over local network on port 38899.
- **Ambient AI Lifecycle Signaling**:
  - 🔵 **Blue**: Agent is waiting for user confirmation or input (`wiz signal blue`).
  - 🔴 **Red**: An error, test failure, or exception occurred (`wiz signal red`).
  - 🟢 **Green**: Task or goal successfully completed (`wiz signal green`). Stays green for 10s, then smoothly returns to default.
  - 🛋️ **Warm White (2700K)**: Default working state.
- **High-Contrast Emergency Strobe Alert**: Fast alternation between 10% Warm Amber and 100% Cool Daylight White.
- **Auto-Discovery & MAC Recovery**: Automatic subnet scanning and dynamic IP recovery if DHCP reassigns bulb IPs.
- **Multi-Device & Room Grouping**: Target individual bulbs (`lamp`, `tbulb`), whole rooms (`myroom`), or all devices (`all`).

## Quick CLI Reference

```bash
# Check status of all bulbs
wiz status

# Ambient AI status signals
wiz signal blue            # Waiting for user input / confirmation
wiz signal red             # Error or failure occurred
wiz signal green           # Task successfully completed (auto-reverts in 10s)
wiz signal warm            # Restore default warm white

# Lamp controls (A60 RGBW Color Bulb)
wiz lamp on
wiz lamp off
wiz lamp red / green / blue / purple / cyan / orange / yellow / pink
wiz lamp warm / cool / neutral / reading / cozy
wiz lamp dim 50

# Ceiling T-Bulb controls
wiz t bulb on
wiz t bulb off
wiz t bulb warm / cool / neutral / reading / focus
wiz t bulb dim 80
wiz t bulb alert           # High-contrast strobe alert

# Multi-bulb grouping
wiz myroom on              # Turn on both room lights
wiz myroom off             # Turn off both room lights
wiz all off                # Turn off all home lights
```
