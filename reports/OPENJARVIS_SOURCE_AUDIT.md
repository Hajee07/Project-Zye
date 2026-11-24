# OpenJarvis Source Archive Forensic Audit Report

**Project:** ZYE AI Hybrid Personal Windows AI Assistant  
**Archive:** `D:\Zye\OpenJarvis-main.zip`  
**Reference Extraction Directory:** `D:\Zye\references\OpenJarvis-main\`  
**Audit Classification:** Security, License, and Dependency Manifest Audit  
**Date:** 2026-11-24  

---

## 1. Archive Provenance & Cryptographic Verification

| Property | Value | Verification Status |
| :--- | :--- | :---: |
| **Archive File Name** | `OpenJarvis-main.zip` | Verified |
| **File Size (Compressed)** | 42.43 MB (44,491,959 bytes) | Verified |
| **Uncompressed Size** | 101.13 MB (106,043,923 bytes) | Verified |
| **Total Archive Entries** | 2,483 items | Verified |
| **Cryptographic SHA-256** | `245e3e30dbb44abfaefee1f517341ae65ce63f3fdcda39d5ef9ceba3fd9895e5` | Verified |
| **Top-Level Directory** | `OpenJarvis-main/` | Confirmed Single Root |

---

## 2. Security & Path Traversal Pre-Extraction Audit

Prior to extraction, all 2,483 ZIP entry headers were audited:
1. **Path Traversal Check (`..` sequences):** 0 entries found.
2. **Absolute Path Check (Rooted `/` or drive letters `C:`):** 0 entries found.
3. **Symlink / Hardlink Entries:** No unsafe symbolic or junction links detected.
4. **Compression Ratio:** $101.13\text{ MB} / 42.43\text{ MB} \approx 2.38:1$ (safe, not a decompression bomb).
5. **Bundled Binaries & Executables:** No unsigned binary executables were executed or integrated into the system path. All source inspection is performed strictly as static reference code.

---

## 3. License & Version Manifest Audit

- **License Identification:** Apache License 2.0 (`LICENSE` file verified at archive root).
- **Frontend Version Manifest:** `frontend/package.json` declares name `"openjarvis-chat"` and version `"1.0.1"`.
- **Python Project Manifest:** `pyproject.toml` declares project name `"OpenJarvis"` with dynamic VCS version resolution (`dynamic = ["version"]`). In accordance with Section 03, no artificial Python release version is invented.
- **Third-Party Attribution:** Documented in `docs/THIRD_PARTY_NOTICES.md` to preserve all required Apache 2.0 notices and attribution.

---

## 4. Subsystem Layout in Reference Source

- `src/openjarvis/core/`: Event bus, type system, registries, configuration.
- `src/openjarvis/engine/`: Cloud, Ollama, multi-engine interfaces.
- `src/openjarvis/intelligence/`: Model catalog and capability metadata.
- `src/openjarvis/learning/routing/`: Query complexity, heuristic routing.
- `src/openjarvis/agents/`: Agent execution, loop guard (`loop_guard.py`).
- `src/openjarvis/security/`: Capability-based security, injection scanner, credential stripper.
- `src/openjarvis/memory/`: Fact store, background extraction service, hybrid retrieval.
- `src/openjarvis/scheduler/`: Persistent cron/interval task scheduling.
- `src/openjarvis/telemetry/`: Resource metrics, execution tracing.
- `desktop/src-tauri/src/overlay.html`: Minimal floating HUD desktop overlay.
- `crates/`: Rust acceleration crates (optional, reference only).
- `deploy/windows/`: Scheduled task and PowerShell service patterns.

---

## 5. Security Boundary & Operational Constraints
- **Isolation Policy:** The reference archive is retained in `references/OpenJarvis-main/` as a design and selective source reference.
- **No Direct Dependency Sync:** Full `pip install` or `uv sync --all-extras` of OpenJarvis is explicitly blocked to protect ZYE's stable virtual environment.
- **Zero Double-Agent Deployment:** OpenJarvis is never executed as a standalone background daemon or second assistant. All capabilities are selectively adapted into ZYE's Master Brain.
