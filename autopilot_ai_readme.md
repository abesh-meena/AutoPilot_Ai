# AutoPilot AI – Browser Automation Agent

AutoPilot AI is a real browser‑automation agent that performs **human‑like actions inside any website** (YouTube, Google, LinkedIn, Instagram, etc.) based on natural language instructions. It does not generate summaries only — it performs **actual clicks, scrolls, searches, typing, navigation, and page actions** in a real Chrome browser.

This project is designed as a **Chrome Extension + AI Task Planner** that enables full automation inside the browser.

---

## ⭐ Project Overview
AutoPilot AI is an intelligent agent capable of:
- Opening websites automatically (YouTube, Google, LinkedIn, etc.)
- Reading natural language tasks
- Translating tasks into actions
- Executing those actions directly inside the browser using a content‑script automation engine
- Navigating, clicking buttons, filling forms, scrolling pages
- Fetching information from the current webpage
- Returning structured output to the user

This behaves like a **human operating the browser** — not just data scraping.

---

## 🎯 Main Features
### ✔ **Real Browser Automation**
- YouTube open karna
- Search bar me text type karna
- Videos click karna
- Page scroll karna
- Google search karna
- LinkedIn me jobs search karna
- Instagram open & interact karna

### ✔ **Natural Language Commands**
Examples:
- “YouTube kholo aur lofi playlist search karo”
- “Google open karo, ‘AI news today’ search karo”
- “LinkedIn par AI jobs search karo aur first 5 results do”
- “Page scroll down kar do”
- “Is button ko click karo”

### ✔ **AI Task Planner**
- User ke sentence ko action steps me convert karta hai:
  - openUrl
  - typeText
  - clickElement
  - scrollPage
  - extractContent

### ✔ **Action Execution Engine**
- Each action browser ke andar execute hota hai using DOM automation.

### ✔ **Chrome Extension Based**
- Manifest V3 compatible
- Works on all Chromium browsers
- Popup UI + background + content scripts

### ✔ **Safe & Controlled**
- Only browser ke andar kaam karta
- Laptop ki system windows, files, apps ko control nahi karta

---

## 🏗 Project Architecture
Complete architecture is divided into 3 logical layers:

```
AutoPilot-AI/
│
├── extension/
│   ├── manifest.json
│   ├── background.js  # message routing + AI communication
│   ├── content.js     # real browser automation actions
│   ├── popup.html      
│   ├── popup.js
│   └── styles.css
│
├── backend/
│   ├── app.py          # FastAPI web server
│   ├── llm_planner.py  # natural language → action plan
│   ├── action_schema.py
│   └── utils/
│       └── extractor.py
│
├── docs/
│   └── architecture_diagram.png
│
└── README.md
```

---

## 🧠 How AutoPilot AI Works

### **1. User Writes a Command**
Example: “YouTube kholo aur lofi playlist search karo.”

### **2. Extension Sends Command to Backend**
Natural language → AI Task Planner

### **3. AI Creates a Step‑by‑Step Action Plan**
```
[
  { action: "openUrl", url: "https://www.youtube.com" },
  { action: "typeText", selector: "input#search", text: "lofi playlist" },
  { action: "keyPress", key: "Enter" }
]
```

### **4. Extension Executes Actions**
Content script real browser ke andar:
- `document.querySelector(...)`
- `.click()`
- `.value = "text"`
- `window.scrollTo(...)`

### **5. User Sees Result**
UI me status + fetched info display hota.

---

## 🧩 Key Components

### **1. Chrome Extension (Frontend of Agent)**
- Popup interface
- Command input box
- Background process for message routing
- Content script for executing actions

### **2. AI Backend (Brain of Agent)**
- LLM-based task planner
- Action classification
- Selector identification (CSS selectors)
- Multi-step execution logic

### **3. Browser Automation Engine**
- Click
- Navigate
- Type
- Scroll
- Extract text
- Find elements

---

## 📌 Example Use Cases
- YouTube Automation
- Google Search Automation
- LinkedIn Job Search
- Amazon product search
- Instagram feed scrolling
- Web-based workflows

---

## 🔐 Security Layer
- Only browser ke DOM ke andar kaam karta hai
- System-level control nahi leta
- No file-system access
- User permission required
- Sandboxed environment

---

## 🌐 Future Enhancements
- Voice-command support
- Auto-login using cookies API
- Multi-step scheduled workflows
- Smart element detection using AI CV models
- Webpage screenshot capture
- User macros (reusable automation scripts)

---

## 📝 Summary (One Paragraph)
AutoPilot AI is a full browser-automation agent that performs real actions inside websites using natural-language commands. It uses a Chrome extension to execute actions like clicking, scrolling, navigating, typing, and extracting information directly on real pages, powered by an AI backend that converts instructions into step-by-step actions. This project demonstrates real-world automation, agentic AI, task planning, DOM manipulation, and browser scripting — making it a strong AI + Automation portfolio project.

---

## 📎 End Note
Ye README kisi ko bhi project ka full idea dedega — how it works, structure, flow, capabilities, and future improvements. Aap isko directly share karke project explain kar sakte ho without speaking anything.

