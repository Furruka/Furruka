# Furruka

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&size=22&duration=2800&pause=900&color=7AA2F7&center=true&vCenter=true&width=720&lines=LOW-LEVEL+SYSTEMS+EXPLORER;LINUX+%2F+ANDROID+%2F+KERNEL;MAINLINE+LINUX+%2F+ARM64+%2F+DRIVERS;BREAKING+THINGS+BELOW+THE+ABSTRACTION+LAYER" />
</p>

<p align="center">
  <a href="https://github.com/Furruka">
    <img src="https://img.shields.io/badge/GitHub-Furruka-24292f?style=flat-square&logo=github" />
  </a>
  <img src="https://img.shields.io/badge/Linux-Enthusiast-FCC624?style=flat-square&logo=linux&logoColor=black" />
  <img src="https://img.shields.io/badge/Android-Kernel-3DDC84?style=flat-square&logo=android&logoColor=white" />
  <img src="https://img.shields.io/badge/ARM64-Developer-0091BD?style=flat-square" />
</p>

---

## `whoami`

> **I build things below the abstraction layer.**

I'm interested in the parts of computing that most applications never need to see:

* 🐧 Linux kernel & system internals
* 📱 Android kernel / custom ROM / GSI
* ⚙️ Mainline Linux on mobile hardware
* 🧩 Device drivers & hardware bring-up
* 🖥️ DRM / display pipeline / Wayland
* 🔬 SoC debugging & reverse engineering
* 🌐 Linux networking & embedded systems

Currently exploring the boundary between **Android hardware and upstream Linux**.

---

## `SYSTEM PROFILE`

```text
┌─────────────────────────────────────────────────────────┐
│                     FURRUKA SYSTEM                      │
├──────────────────┬──────────────────────────────────────┤
│ Primary OS       │ Arch Linux                           │
│ Desktop          │ KDE Plasma / Wayland                │
│ Architecture     │ x86_64 / ARM64                      │
│ Main Language    │ C / C++                              │
│ Scripting        │ Bash / Python                       │
│ Kernel           │ Linux                                │
│ Focus            │ Android / Mainline / Drivers        │
└──────────────────┴──────────────────────────────────────┘
```

---

## `ENGINEERING STACK`

<p align="center">
  <img src="https://skillicons.dev/icons?i=linux,arch,bash,c,cpp,python,git,github,android,cmake,vim,vscode" />
</p>

```text
LOW LEVEL
██████████████████████████████████████  Linux Kernel
██████████████████████████████████░░░░  Android
████████████████████████████████░░░░░░  ARM64
██████████████████████████████░░░░░░░░  Device Drivers

SYSTEMS
████████████████████████████████████░░  Linux
███████████████████████████████░░░░░░░  Networking
█████████████████████████████░░░░░░░░░  Wayland
████████████████████████████░░░░░░░░░░  Embedded

LANGUAGES
████████████████████████████████████░░  C
███████████████████████████████░░░░░░░  C++
████████████████████████████░░░░░░░░░  Python
██████████████████████████░░░░░░░░░░░  Shell
```

---

## `CURRENTLY BUILDING`

### 🐧 Mainline Linux

Bringing modern Linux to hardware originally designed around vendor Android kernels.

```text
Vendor Kernel
     │
     ├── DTS
     ├── Drivers
     ├── Firmware
     └── Hardware quirks
          │
          ▼
     Mainline Linux
          │
          ├── DRM
          ├── Display
          ├── Power
          ├── Audio
          └── SoC
```

### 📱 Android / Linux

Exploring the relationship between:

```text
Android
   │
   ├── AOSP
   ├── GKI
   ├── Vendor Modules
   └── HAL
        │
        ▼
Linux Kernel
   │
   ├── DRM
   ├── Media
   ├── GPU
   ├── Audio
   └── SoC
```

---

## `PROJECT LAB`

<table>
<tr>
<td width="50%">

### 🐧 Kernel

Linux kernel development, debugging and upstream-oriented work.

**Focus**

`Kernel` · `Drivers` · `ARM64` · `DTS`

</td>

<td width="50%">

### 📱 Android

Custom kernels, ROMs, GSI and Android/Linux integration.

**Focus**

`AOSP` · `GKI` · `GSI` · `Custom ROM`

</td>
</tr>

<tr>
<td>

### 🖥️ Display

DRM/KMS, display pipelines and mobile display hardware.

**Focus**

`DRM` · `DSI` · `DSC` · `Wayland`

</td>

<td>

### 🌐 Networking

Linux networking, DNS, routing and embedded systems.

**Focus**

`DNS` · `nftables` · `TProxy` · `Router`

</td>
</tr>
</table>

---

## `GITHUB TELEMETRY`

<p align="center">
  <img height="170" src="https://github-readme-stats.vercel.app/api?username=Furruka&show_icons=true&hide_border=true&count_private=true" />
  <img height="170" src="https://github-readme-stats.vercel.app/api/top-langs/?username=Furruka&layout=compact&hide_border=true" />
</p>

<p align="center">
  <img src="https://streak-stats.demolab.com?user=Furruka&hide_border=true" />
</p>

---

## `ACTIVITY MAP`

<p align="center">
  <img src="https://github-readme-activity-graph.vercel.app/graph?username=Furruka&hide_border=true" />
</p>

---

## `DEVELOPMENT LOG`

```text
2026 ────────────────────────────────────────────────

[01] Android Kernel
     └─ Kernel bring-up / debugging

[02] Mainline Linux
     └─ ARM64 / SoC / upstream development

[03] Display
     └─ DRM / DSI / DSC / KMS

[04] Linux Desktop
     └─ Arch Linux / KDE / Wayland

[05] Networking
     └─ DNS / nftables / embedded routing
```

---

## `TOOLS I LIVE IN`

```text
OS              Arch Linux
Desktop         KDE Plasma
Session         Wayland
Shell           Bash
Editor          Vim / VS Code
Build           Make / CMake / Ninja
Version Control Git
Debugging       GDB / printk / ftrace
```

---

## `PHILOSOPHY`

> **If the abstraction leaks, go one layer deeper.**

```text
Application
     ↓
Framework
     ↓
Userspace
     ↓
Kernel
     ↓
Driver
     ↓
Hardware
     ↓
       ← this is where things get interesting
```

---

## `OPEN SOURCE`

Most of my work lives around Linux, Android and hardware.

If something here is useful to you:

**⭐ Star it · 🐛 Report it · 🔧 Improve it**

That's what open source is about.

---

## `CONTRIBUTION`

<p align="center">
  <img src="https://raw.githubusercontent.com/Furruka/Furruka/output/github-contribution-grid-snake.svg" />
</p>

---

<p align="center">

`Furruka` · Linux · Android · Kernel · Mainline

**Thanks for stopping by.**

</p>
