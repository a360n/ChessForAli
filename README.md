<div align="center">

# ChessForAli — Automated Chess Game Analysis & HD Video Generation Engine

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Stockfish](https://img.shields.io/badge/Stockfish-16_UCI-000000?style=for-the-badge&logo=chess.com&logoColor=white)](https://stockfishchess.org/)
[![MoviePy](https://img.shields.io/badge/FFmpeg-MoviePy_Renderer-FF0000?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://zulko.github.io/moviepy/)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--Time_Progress-4E9A06?style=for-the-badge&logo=socketdotio&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

<p align="center">
  A high-throughput backend pipeline that converts chess PGN games into annotated, high-definition animated videos with deep <b>Stockfish NNUE</b> engine evaluation, dynamic win-rate bars, piece sound effects, and real-time <b>WebSocket</b> progress tracking.
</p>

</div>

---

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Key Features](#key-features)
- [Core Pipeline Modules](#core-pipeline-modules)
- [API Reference](#api-reference)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Author & License](#author--license)

---

## Overview

**ChessForAli** (Chess2Video Engine) is a specialized media automation system engineered in Python. It ingests standard chess move notations (PGN / UCI) and programmatically synthesizes 1080p 60FPS video breakdowns. Each rendered move is evaluated in real time using the Stockfish chess engine to produce dynamic evaluation gauges, contextual move annotations, and synchronized tactical audio cues.

### Core Problems Solved
- **Automated Content Generation:** Eliminates manual screen recording and editing for chess content creators and coaches.
- **Deep Engine Evaluation:** Seamless integration with UCI Stockfish binaries for millisecond-level position scoring (centipawns and win-probability sigmoid curves).
- **Asynchronous Scalability:** FastAPI task queuing with WebSocket duplex telemetry for non-blocking multi-user rendering.

---

## System Architecture

```mermaid
flowchart TD
    subgraph ClientLayer["Client & Web Interface"]
        User["Client Request
(PGN / Moves / Theme Config)"]
        WSClient["WebSocket Progress Listener"]
    end

    subgraph FastAPIServer["FastAPI Application Server (main.py)"]
        APIRoute["REST Endpoint (/generate)"]
        TaskManager["Task Manager & Background Workers"]
        WSHub["WebSocket Event Dispatcher"]
    end

    subgraph ProcessingPipeline["Core Rendering Pipeline"]
        ChessLogic["FEN & Board State Validator
(chess_logic.py)"]
        StockfishWorker["Stockfish 16 NNUE Engine
(stockfish_helper.py)"]
        FrameSynthesizer["PIL / Canvas Frame Generator
(video_engine.py)"]
        AudioMixer["Audio Synthesizer
(Move, Capture & Check SFX)"]
        FFmpegEncoder["FFmpeg / MoviePy Video Compiler
(H.264 / AAC Encoding)"]
    end

    subgraph Storage["Artifact Output"]
        VideoFile["Exported MP4 Video (/output/*.mp4)"]
    end

    User -->|POST /generate| APIRoute
    APIRoute --> TaskManager
    TaskManager --> ChessLogic
    ChessLogic --> StockfishWorker
    StockfishWorker --> FrameSynthesizer
    FrameSynthesizer --> AudioMixer
    AudioMixer --> FFmpegEncoder
    FFmpegEncoder --> VideoFile
    TaskManager -.->|Progress Updates (0-100%)| WSHub
    WSHub -.->|Live Telemetry| WSClient
```

---

## Key Features

### 1. Stockfish NNUE Evaluation Engine
- Interacts directly with the Stockfish binary through non-blocking UCI pipes.
- Calculates exact centipawn scores, mate-in-N sequences, and computes non-linear win probability using a logistic sigmoid function:
  $$	ext{Win Probability} = rac{1}{1 + 10^{-rac{	ext{centipawns}}{400}}}$$
- Generates smooth sidebar evaluation bars that dynamically rise or fall as the game progresses.

### 2. High-Definition Visual Synthesizer
- Multi-theme vector and raster asset rendering (supports `alpha`, `cburnett`, `staunty`, and `fantasy` piece sets).
- Automated board layout generator with coordinate markings, highlighted last moves, check alerts, and legal move indicators.
- Native image processing optimization using PIL (Pillow) and macOS `sips` vector rasterizer.

### 3. Synchronized Spatial Audio
- Context-aware sound trigger engine playing crisp acoustic feedback for:
  - Standard pawn/piece moves
  - Captures and sacrifices
  - Checks, checkmates, and countdown warnings

### 4. Asynchronous Task Queue & WebSockets
- Background task dispatch allowing long-running renders to execute without blocking the main event loop.
- Real-time frame rendering percentages streamed directly to connected frontends via WebSockets.

---

## Core Pipeline Modules

| Module | Responsibility | Key Classes & Functions |
| :--- | :--- | :--- |
| **`main.py`** | Application server, routing, background workers, WebSockets | `FastAPI`, `tasks_status`, `ws_clients` |
| **`video_engine.py`** | Frame generation, theme conversion, MoviePy clip assembly | `VideoEngine.generate_video()` |
| **`stockfish_helper.py`** | Subprocess pipe to Stockfish, UCI protocol handler, eval parser | `StockfishHelper.analyze_position()` |
| **`chess_logic.py`** | FEN notation parsing, board matrix representation, move execution | `Board.load_fen()`, `Board.make_move()` |
| **`upload_server.py`** | Asset and wheel dependency upload endpoint | `FastAPI` file receiver |

---

## API Reference

### 1. Initiate Video Generation
```http
POST /generate
Content-Type: application/json

{
  "moves": ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5"],
  "theme": "cburnett",
  "fps": 30,
  "depth": 12,
  "include_eval_bar": true
}
```

**Response:**
```json
{
  "task_id": "c8a4128f-7f61-419b-a621-e77c47d79b9c",
  "status": "processing",
  "websocket_url": "/ws/c8a4128f-7f61-419b-a621-e77c47d79b9c"
}
```

### 2. WebSocket Telemetry Stream
Connect to `ws://localhost:8000/ws/{task_id}` to receive real-time JSON frames:
```json
{
  "progress": 72,
  "current_move": "Nf3",
  "eval": "+0.45",
  "status": "rendering_frames"
}
```

---

## Tech Stack

- **Primary Language:** Python 3.10+
- **API Framework:** FastAPI, Uvicorn, Pydantic
- **Chess Analytics:** Stockfish 16 (Apple Silicon / x86-64 binary), python-chess
- **Graphics & Composition:** Pillow (PIL), CairoSVG, MoviePy
- **Video & Audio Encoding:** FFmpeg (libx264, aac)
- **Protocol:** RESTful JSON, WebSockets (RFC 6455)

---

## Project Structure

```
ChessForAli/
├── main.py                  # FastAPI Application Entry & WebSockets Hub
├── video_engine.py          # Core Frame & Clip Synthesizer
├── stockfish_helper.py      # Stockfish 16 Engine UCI Interface
├── chess_logic.py           # Pure Python FEN Parser & Move Validator
├── upload_server.py         # Utility Upload Server
├── verify_system.py         # System Pre-flight & Dependency Diagnostics
├── requirements.txt         # Production Python Dependencies
├── assets/                  # Graphical & Audio Assets
│   ├── pieces/              # SVG Vector Piece Themes (alpha, cburnett, staunty)
│   ├── pieces_png/          # Pre-rendered High-Res PNG Sprites
│   └── sounds/              # Soundboard (standard chess effects)
├── stockfish/               # Native Stockfish Engine Binaries & Source
│   └── stockfish-macos-m1-apple-silicon
├── templates/               # HTML5 Web UI Templates
└── output/                  # Compiled MP4 Video Destination
```

---

## Getting Started

### Prerequisites
- Python 3.10 or higher
- FFmpeg installed (`brew install ffmpeg` on macOS)
- Native Stockfish binary configured in `stockfish/`

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/a360n/ChessForAli.git
   cd ChessForAli
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify System Dependencies:**
   ```bash
   python3 verify_system.py
   ```

5. **Start the Video Engine Server:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Access the interactive Swagger documentation at `http://localhost:8000/docs`.

---

## Author

**Ali Nasser (Ali Al-Khazali)**
- Portfolio: [www.ali-nasser.dev](https://www.ali-nasser.dev)
- GitHub: [@a360n](https://github.com/a360n)
- LinkedIn: [Ali Nasser](https://linkedin.com/in/alinasser)

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
