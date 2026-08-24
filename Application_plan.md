# Implementation Plan: Commlink Two-Way Radio GUI Application

**Commlink** is a modern, responsive Two-Way Radio Communication Application. It interfaces seamlessly with GNU Radio via the established Hot-Folder Synchronization architecture, providing user authentication, manual node addressing, real-time chat, and multi-media file transmission (Images, PDFs, Audio, and Text) with file-type validation and inline previews.

---

## User Review Required

> [!IMPORTANT]
> **Architecture Decision: Python FastAPI Backend + Pure Vanilla Web Frontend**
> - **Backend**: Lightweight Python FastAPI service that interfaces directly with local `transfers/node_<id>/` directories, watches for incoming files in real-time, and communicates with the frontend via WebSockets and REST APIs.
> - **Frontend**: State-of-the-art dark-mode glassmorphic interface (HTML5, Vanilla CSS, Vanilla JavaScript) with inline audio players, image lightbox, PDF download cards, and attachment type validators.
> - **Zero External Build Tools Required**: Runs instantly via standard Python libraries without needing complex Node.js/NPM builds.

---

## Proposed System Architecture

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      COMMLINK WEB FRONTEND (Browser)                   │
 │   - Sign Up / Log In (Node Address configuration: e.g. Node 1)         │
 │   - Chat Interface with Destination Selector (Node 2..254, Broadcast)  │
 │   - Attachment Validator (Image, PDF, Audio, Text)                     │
 │   - Inline Audio Player, Image Previews, PDF Download Cards            │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ (HTTP REST / WebSocket Live Stream)
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │               COMMLINK BACKEND SERVER (apps/commlink/server.py)        │
 │   - User Authentication & Account Store (`users.json`)                 │
 │   - TX Manager: Saves text/attachments to `transfers/node_src/tx/`     │
 │   - RX Watcher: Real-time observer on `transfers/node_src/rx/`         │
 │   - Pushes live incoming radio messages to UI via WebSockets           │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ (File System I/O)
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │         GNU RADIO HOT-FOLDER SYNC & TRANSPORT LAYER                    │
 │   - `folder_sync_daemon.py` + `test_socket_sync.grc`                   │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## Proposed Changes & File Additions

### 1. Commlink Application Package (`apps/commlink/`)

#### [NEW] [server.py](file:///home/methalabeywickrama/Documents/CDP%20Project/twowaycomdevice/apps/commlink/server.py)
- FastAPI / ASGI HTTP + WebSocket server.
- Endpoints:
  - `POST /api/signup`: Creates account with username, password, display name, and Node Address (`1..254`).
  - `POST /api/login`: Validates credentials and issues session token.
  - `POST /api/logout`: Terminates active session.
  - `GET /api/me`: Returns current user profile and node address.
  - `GET /api/contacts`: Returns known node addresses & contacts list.
  - `GET /api/messages`: Returns message history with selected contact.
  - `POST /api/send`: Sends text message or file attachment. Validates file type and writes to `transfers/node_<src>/tx/node_<dst>/`.
  - `WS /ws`: WebSocket live feed for incoming received files from `transfers/node_<src>/rx/`.

#### [NEW] [index.html](file:///home/methalabeywickrama/Documents/CDP%20Project/twowaycomdevice/apps/commlink/static/index.html)
- Modern, accessible single-page layout:
  - **Auth Modal / View**: Sign Up & Log In screens with node address entry, validation, and profile selection.
  - **Main Dashboard**:
    - **Top Bar**: Commlink logo, Node ID badge (e.g. `Node 1 [ONLINE]`), Radio RF Link status, user menu, and Log Out button.
    - **Sidebar**: Destination node contact list (`Node 2`, `Node 3`, `Broadcast 0`), recent conversation snippets, unread badges.
    - **Chat Feed**: Bubble messages with timestamps, sender badges, inline image thumbnails, playable audio widgets, PDF document cards.
    - **Attachment & Message Bar**:
      - Text input box.
      - Attachment button with popup filter (`📷 Image`, `📄 PDF Document`, `🎵 Audio Clip`, `📁 Any File`).
      - Client-side validation with instant file type / size error alerts.
      - Send button with loading spinner during radio transmission.

#### [NEW] [style.css](file:///home/methalabeywickrama/Documents/CDP%20Project/twowaycomdevice/apps/commlink/static/style.css)
- Premium dark aerospace/cyberpunk theme:
  - Color palette: Deep space navy background (`#0B0F19`), card glassmorphism (`#151C2C/80`), cyan accent (`#00E5FF`), emerald success (`#00E676`), amber warning (`#FFB300`).
  - Modern typography: Google Inter font with clean line heights.
  - Smooth micro-animations for message entry, attachment chips, and modal transitions.

#### [NEW] [app.js](file:///home/methalabeywickrama/Documents/CDP%20Project/twowaycomdevice/apps/commlink/static/app.js)
- Application client logic:
  - Auth state management (JWT/localStorage).
  - WebSocket auto-reconnect and real-time message stream.
  - File attachment validator (checking file extensions: `.png`, `.jpg`, `.jpeg`, `.webp`, `.pdf`, `.wav`, `.mp3`, `.ogg`, `.txt`).
  - Multimedia renderers (HTML5 `<audio>` player, lightbox modal for full-size images, PDF download triggers).

#### [NEW] [run_commlink.sh](file:///home/methalabeywickrama/Documents/CDP%20Project/twowaycomdevice/run_commlink.sh)
- One-click launcher script starting both the Commlink web server and the background folder sync daemon.

---

## Verification Plan

### Automated Verification
1. Test server APIs via Python test script (`tests/test_commlink_api.py`):
   - Register User 1 (Node 1) and User 2 (Node 2).
   - Log in and verify session authentication.
   - Send text message from Node 1 $\to$ Node 2 and verify file creation in `transfers/node_1/tx/node_2/`.
   - Send image, PDF, and audio attachment with validation checking.
   - Verify invalid file rejection (e.g. attempting to send unsupported formats).
2. End-to-end integration test with GNU Radio flowgraph.

### Manual Verification
1. Launch Commlink via `bash run_commlink.sh`.
2. Open `http://localhost:8000` in browser.
3. Sign up with Node Address `1`, log in, switch destination to `Node 2`.
4. Type a message, attach an image and PDF, click **Send**.
5. Observe live transmission and delivery in the chat interface.
