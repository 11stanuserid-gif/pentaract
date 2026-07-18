#!/usr/bin/env python3
"""
Signup Shield Auditor — Backend API
FastAPI server that wraps the Playwright-based security testing engine.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Add core to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.security_tester import SecurityTester
from core.report_generator import ReportGenerator

# ── Logging ──────────────────────────────────────────────────────────
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("api")

# ── App setup ────────────────────────────────────────────────────────
app = FastAPI(title="Signup Shield Auditor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory audit state ────────────────────────────────────────────
audits: Dict[str, dict] = {}

# ── Pydantic models ──────────────────────────────────────────────────

class AuditRequest(BaseModel):
    target_url: str = Field(..., description="The signup page URL to test")
    num_accounts: int = Field(default=5, ge=1, le=1000, description="Number of test accounts")
    delay_mode: str = Field(default="auto", description="Delay mode: auto, fast, normal, stealth, custom")
    delay_min: float = Field(default=2.0, ge=0.5, le=60.0, description="Min delay between signups (sec)")
    delay_max: float = Field(default=5.0, ge=0.5, le=60.0, description="Max delay between signups (sec)")
    headless: bool = Field(default=True, description="Run browser in headless mode")
    weak_password_pct: float = Field(default=0, ge=0, le=100, description="% of accounts with weak passwords")
    captcha_api_key: str = Field(default="", description="CAPTCHA solving API key (capsolver or 2captcha)")
    captcha_service: str = Field(default="capsolver", description="CAPTCHA service: capsolver or 2captcha")
    test_captcha: bool = Field(default=True)
    test_rate_limit: bool = Field(default=True)
    test_email_verify: bool = Field(default=True)
    test_fingerprint: bool = Field(default=True)
    test_password_policy: bool = Field(default=True)
    test_duplicate: bool = Field(default=True)


class AuditStatus(BaseModel):
    audit_id: str
    status: str  # "running" | "completed" | "failed"
    progress: float = 0.0
    current_step: str = ""
    log_lines: list = []


# ── Helpers ──────────────────────────────────────────────────────────

def _make_progress_callback(audit_id: str):
    """Return a progress callback that updates the in-memory audit state."""

    def _cb(current: int, total: int, message: str):
        state = audits.get(audit_id)
        if state is None:
            return
        pct = (current / total) * 100 if total > 0 else 0
        state["progress"] = pct
        state["current_step"] = message
        state["log_lines"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        # Keep last 500 lines
        if len(state["log_lines"]) > 500:
            state["log_lines"] = state["log_lines"][-500:]

    return _cb


# ── Routes ───────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/api/audit")
async def start_audit(req: AuditRequest):
    """Start a new security audit and return its ID."""
    audit_id = uuid.uuid4().hex[:12]

    audits[audit_id] = {
        "status": "running",
        "progress": 0.0,
        "current_step": "Initializing...",
        "log_lines": [],
        "result": None,
        "error": None,
        "request": req.model_dump(),
    }

    # Launch background task
    asyncio.create_task(_run_audit(audit_id, req))

    return {"audit_id": audit_id, "status": "running"}


@app.get("/api/audit/{audit_id}/status")
async def get_audit_status(audit_id: str):
    """Get the current status of an audit."""
    state = audits.get(audit_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Audit not found")

    return {
        "audit_id": audit_id,
        "status": state["status"],
        "progress": state["progress"],
        "current_step": state["current_step"],
        "log_lines": state["log_lines"][-50:],  # last 50 lines
    }


@app.get("/api/audit/{audit_id}/report")
async def get_audit_report(audit_id: str):
    """Get the final report of a completed audit."""
    state = audits.get(audit_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Audit not found")
    if state["status"] == "running":
        raise HTTPException(status_code=400, detail="Audit is still running")
    if state["status"] == "failed":
        return JSONResponse(
            status_code=200,
            content={"audit_id": audit_id, "status": "failed", "error": state["error"]},
        )

    return {"audit_id": audit_id, "status": "completed", "report": state["result"]}


@app.get("/api/reports")
async def list_reports():
    """List all generated HTML reports."""
    if not REPORTS_DIR.exists():
        return {"reports": []}

    files = []
    for f in sorted(REPORTS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix in (".html", ".json") and f.name != "audit.log":
            audit_id_for_file = _find_audit_id_for_report(f.name)
            files.append({
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                "audit_id": audit_id_for_file,
            })

    return {"reports": files}


@app.get("/api/reports/{filename}")
async def get_report_file(filename: str):
    """Serve a report file directly."""
    # Prevent path traversal
    safe_path = REPORTS_DIR / filename
    safe_path = safe_path.resolve()
    if not str(safe_path).startswith(str(REPORTS_DIR.resolve())):
        raise HTTPException(status_code=403, detail="Invalid path")
    if not safe_path.exists() or not safe_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(str(safe_path))


def _find_audit_id_for_report(filename: str) -> Optional[str]:
    """Try to find which audit ID produced a given report file."""
    # Simple heuristic: check if any completed audit has a matching report path
    for aid, state in audits.items():
        if state.get("html_report_path") and state["html_report_path"].endswith(filename):
            return aid
    return None


# ── Background audit runner ──────────────────────────────────────────

async def _run_audit(audit_id: str, req: AuditRequest):
    """Run the security audit in the background and store results."""
    state = audits[audit_id]

    try:
        # Resolve delay range based on delay_mode
        dm = req.delay_mode
        if dm == "auto":
            base = max(1.0, min(10.0, req.num_accounts / 5))
            delay_range = (base * 0.5, base * 1.5)
        elif dm == "fast":
            delay_range = (0.5, 1.5)
        elif dm == "normal":
            delay_range = (2.0, 5.0)
        elif dm == "stealth":
            delay_range = (5.0, 15.0)
        else:  # custom
            delay_range = (req.delay_min, req.delay_max)

        tester = SecurityTester(
            target_url=req.target_url,
            num_accounts=req.num_accounts,
            delay_range=delay_range,
            headless=req.headless,
            proxy_list=[],
            test_captcha=req.test_captcha,
            test_rate_limit=req.test_rate_limit,
            test_email_verify=req.test_email_verify,
            test_fingerprint=req.test_fingerprint,
            test_password_policy=req.test_password_policy,
            test_duplicate=req.test_duplicate,
            weak_password_ratio=req.weak_password_pct / 100,
            captcha_api_key=req.captcha_api_key,
            captcha_service=req.captcha_service,
        )

        callback = _make_progress_callback(audit_id)
        results = await tester.run_all_tests(callback)

        # Generate reports
        report_gen = ReportGenerator(output_dir=str(REPORTS_DIR))
        html_path = report_gen.generate(results)
        json_path = report_gen.generate_json_report(results)

        state["result"] = results
        state["html_report_path"] = html_path
        state["json_report_path"] = json_path
        state["status"] = "completed"
        state["progress"] = 100.0
        state["current_step"] = "Audit complete!"
        state["log_lines"].append(f"[{datetime.now().strftime('%H:%M:%S')}] Audit complete!")
        state["log_lines"].append(f"[{datetime.now().strftime('%H:%M:%S')}] Score: {results['security_score']['overall_percentage']}%")

    except Exception as e:
        logger.exception(f"Audit {audit_id} failed")
        state["status"] = "failed"
        state["error"] = str(e)
        state["log_lines"].append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {e}")


# ── Entry point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
