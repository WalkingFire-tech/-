<div align="center">

# Alliance Pioneer

### A Self-Evolving Cognitive AI System

**从"执行函数"到"求解真相"的认知行动者**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/WalkingFire-tech/Alliance-Pioneer/actions/workflows/ci.yml/badge.svg)](https://github.com/WalkingFire-tech/Alliance-Pioneer/actions/workflows/ci.yml)
[![Issues](https://img.shields.io/github/issues/WalkingFire-tech/Alliance-Pioneer)](https://github.com/WalkingFire-tech/Alliance-Pioneer/issues)

[English](#overview) · [中文](#概述) · [Architecture](#architecture) · [Quick Start](#quick-start) · [API Docs](docs/API.md) · [Philosophy](PHILOSOPHY.md)

</div>

---

## Overview

Alliance Pioneer is not another chatbot. It's a **cognitive agent** that perceives, decomposes, executes, self-reflects, abstracts, consolidates, and evolves — a 7-step closed loop from input to capability growth.

The core question it answers: **Can an AI system learn to solve problems it was never programmed for?**

## 概述

联盟拓荒者不是聊天机器人，而是一个**认知行动者**——感知→分解→执行→自察→抽象→沉淀→进化，七步闭环。它回答的核心问题是：**一个AI系统能否学会解决它从未被编程过的问题？**

---

## Key Features

| Feature | Description |
|---------|-------------|
| **9-Path Parallel Reasoning** | Experience pool, knowledge base, local LLM, external API, rule engine, fact store, self-reasoning, web search, tool execution — all running in parallel, best result selected |
| **CBNR Cognitive Hub** | L1 Predictive Coding → L2 Causal Bottleneck → L3 Residual Reuse — attention-driven dynamic compression |
| **Self-Evolution** | Gene evolution (10 evolvable parameters), skill emergence, truth accumulation, experience consolidation |
| **Autonomous Execution** | Capability creation loop: detect gap → generate code → execute → verify → register as tool |
| **Semantic Scientific Disclaimer** | Not keyword matching — understands response structure (numerical/causal/mechanism claims) and auto-annotates uncertainty |
| **4-Layer Defense** | Prevention → Monitoring → Handling → Repair, with circuit breakers and fault isolation |
| **Existence Layer** | Heartbeat / Growing / Resting / Sleeping — the system has a circadian rhythm |
| **Hardware Access** | Serial port communication, GPS/NMEA parsing, system command execution |

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │         User Input                   │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │     Cognitive Dispatcher             │
                    │  (Semantic Intent Classification)    │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
    ┌─────────▼─────────┐ ┌───────▼───────┐ ┌──────────▼──────────┐
    │  9-Path Parallel   │ │  CBNR Hub     │ │  Capability Creation │
    │  Reasoning Engine  │ │  (L1→L2→L3)  │ │  Loop (Auto-Execute) │
    └─────────┬─────────┘ └───────┬───────┘ └──────────┬──────────┘
              │                    │                     │
              └────────────────────┼────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │     Compare & Select Best            │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │  Essence Reasoner → Disclaimer       │
                    │  → Spirit Verification               │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │     Reflective Learning              │
                    │  (Skill Emergence / Truth / Gene)    │
                    └─────────────────────────────────────┘
```

### Directory Structure

```
alliance_pioneer/
├── backend/                 # FastAPI server, chat orchestrator, SSE streaming
│   ├── main_fast.py        # Entry point (100+ API endpoints)
│   └── services/           # Chat orchestrator, persistent solver, parallel router
├── core/                    # Cognitive core
│   ├── cbnr/               # CBNR cognitive hub (L1/L2/L3)
│   ├── learning/           # 7 learning mechanisms + auto execution loop
│   ├── tools/              # Built-in tools (serial, bash, web search, etc.)
│   ├── presence/           # Existence layer (heartbeat/grow/rest/sleep)
│   ├── memory/             # Multi-dimensional memory
│   ├── cognition/          # Failure classifier, audit logger, experience abstractor
│   ├── self/               # Self-model, self-assessment
│   └── instinct/           # Metabolism orchestrator
├── adapters/                # LLM adapters (Ollama, OpenAI, DeepSeek)
├── infrastructure/          # Database, event bus, vector retrieval, defense
├── frontend/                # Web UI (HTML/JS/CSS)
├── knowledge_base/          # Curated knowledge documents
├── tests/                   # Test suite
└── docs/                    # Architecture docs, session archives
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) with a model installed (e.g., `qwen2.5-coder:7b`)
- Optional: DeepSeek/OpenAI API key for external reasoning

### Install & Run

```bash
# Clone
git clone https://github.com/WalkingFire-tech/Alliance-Pioneer.git
cd Alliance-Pioneer

# Install dependencies
pip install -r requirements.txt

# Configure (optional)
cp .env.example .env
# Edit .env to add API keys

# Start (Windows)
start.bat

# Or start manually
python -m uvicorn backend.main_fast:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

### Docker

```bash
docker-compose up -d
```

---

## Philosophy

> **True intelligence is not giving answers, but helping people find their own.**
> **True kindness is not always being gentle, but daring to be silent when necessary.**
> **True growth is not pursuing perfection, but allowing mistakes, corrections, and persistence in imperfection.**

### Meta-Constitution

| Rule | Meaning |
|------|---------|
| R1 | Unverified truths are poison |
| R2 | Ungraduated restructuring is suicide |
| R3 | Unapproved evolution is betrayal |

See [PHILOSOPHY.md](PHILOSOPHY.md) for the full philosophical framework.

---

## Roadmap

| Milestone | Goal | Status |
|-----------|------|--------|
| **v0.5 Autonomous Actor** | Connect capability_creation_loop, fix execution sandbox | [![GitHub milestone](https://img.shields.io/github/milestones/progress/WalkingFire-tech/Alliance-Pioneer/1)](https://github.com/WalkingFire-tech/Alliance-Pioneer/milestone/1) |
| **v0.6 Result Delivery** | Users see results, not code; auto tool-chain composition | [![GitHub milestone](https://img.shields.io/github/milestones/progress/WalkingFire-tech/Alliance-Pioneer/2)](https://github.com/WalkingFire-tech/Alliance-Pioneer/milestone/2) |
| **v1.0 Companion** | Full 7-step closed loop with self-evolution | [![GitHub milestone](https://img.shields.io/github/milestones/progress/WalkingFire-tech/Alliance-Pioneer/3)](https://github.com/WalkingFire-tech/Alliance-Pioneer/milestone/3) |

---

## Contributing

We welcome all forms of contribution! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**The only requirement: be kind, be open.**

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

*"This is a project that will never be finished. We build a thinking companion together. Take any code, change any direction. The only requirement: stay kind, stay open."*

</div>
