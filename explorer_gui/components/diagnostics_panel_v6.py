# explorer_gui/components/diagnostics_panel_v6.py
"""
Diagnostics Panel (v6) — LOSSLESS VERSION
----------------------------------------
Displays translator + validator diagnostics with filtering, search, and
download options (CSV / JSON / NDJSON / ZIP bundle). The ZIP always contains
the unmodified diagnostics payload (diagnostics_raw.json) and optionally
includes the EMJSON snapshot.

Integration example (in streamlit_app_v5.py or v6 app):

    from explorer_gui.components.diagnostics_panel_v6 import render_diagnostics_panel_v6

    render_diagnostics_panel_v6(
        diagnostics=em_v6.get("diagnostics", []),
        em_v6=em_v6,
        title="Translator + Validation Diagnostics"
    )
"""

from __future__ import annotations
import io
import json
import re
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Union
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_diagnostics_panel_v6(
    diagnostics: Union[List[Mapping[str, Any]], List[str], None],
    *,
    em_v6: Optional[Mapping[str, Any]] = None,
    title: str = "Diagnostics",
    default_filename_stem: Optional[str] = None,
) -> None:
    """Render diagnostics with filters and download controls (lossless)."""
    st.markdown(f"### {title}")

    # keep raw diagnostics for lossless export
    raw_payload = diagnostics if isinstance(diagnostics, list) else list(diagnostics or [])
    df = _normalize_for_table_view(raw_payload)

    if df.empty:
        st.info("No diagnostics to display.")
        _render_save_controls(raw_payload, df, em_v6, _pick_stem(em_v6, default_filename_stem))
        return

    # filters
    cols = st.columns([1, 1, 2, 1.4])
    with cols[0]:
        levels = sorted([lvl for lvl in df["level"].unique() if lvl])
        level_filter = st.multiselect("Level", options=levels, default=levels)
    with cols[1]:
        codes = sorted([c for c in df["code"].unique() if c])
        default_codes = codes[: min(12, len(codes))]
        code_filter = st.multiselect("Code", options=codes, default=default_codes)
    with cols[2]:
        search_text = st.text_input("Search message/path/context", "")
    with cols[3]:
        stage_opts = sorted([s for s in df["stage"].unique() if s])
        stage_filter = st.multiselect("Stage", options=stage_opts, default=stage_opts)

    filtered = df.copy()
    if level_filter:
        filtered = filtered[filtered["level"].isin(level_filter)]
    if code_filter:
        filtered = filtered[filtered["code"].isin(code_filter)]
    if stage_filter:
        filtered = filtered[filtered["stage"].isin(stage_filter)]
    if search_text:
        s = search_text.lower()
        mask = (
            filtered["message"].str.lower().str.contains(s, na=False)
            | filtered["path"].str.lower().str.contains(s, na=False)
            | filtered["context"].str.lower().str.contains(s, na=False)
        )
        filtered = filtered[mask]

    st.caption(f"{len(filtered)} of {len(df)} messages shown")
    st.dataframe(
        filtered[["ts", "level", "code", "stage", "path", "message", "context", "source"]],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    _render_save_controls(raw_payload, filtered, em_v6, _pick_stem(em_v6, default_filename_stem))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

REQUIRED_COLS = ["level", "code", "message", "path", "context", "stage", "ts", "source"]

def _normalize_for_table_view(
    diagnostics: Union[List[Mapping[str, Any]], List[str], None]
) -> pd.DataFrame:
    if not diagnostics:
        return pd.DataFrame(columns=REQUIRED_COLS)
    rows = []
    now_iso = datetime.now().isoformat(timespec="seconds")
    for item in diagnostics:
        if isinstance(item, Mapping):
            row = {k: _safe_str(item.get(k, "")) for k in REQUIRED_COLS}
            if not row["level"]:
                row["level"] = _guess_level_from_text(row["message"])
            if not row["ts"]:
                row["ts"] = now_iso
            rows.append(row)
        elif isinstance(item, str):
            rows.append({
                "level": _guess_level_from_text(item),
                "code": "",
                "message": item,
                "path": "",
                "context": "",
                "stage": "",
                "ts": now_iso,
                "source": "",
            })
        else:
            rows.append({
                "level": "",
                "code": "",
                "message": repr(item),
                "path": "",
                "context": "",
                "stage": "",
                "ts": now_iso,
                "source": "",
            })
    df = pd.DataFrame(rows, columns=REQUIRED_COLS)
    try:
        df["_ts"] = pd.to_datetime(df["ts"], errors="coerce")
        df = df.sort_values(by="_ts", ascending=True).drop(columns=["_ts"])
    except Exception:
        pass
    return df.reset_index(drop=True)


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (str, int, float)):
        return str(v)
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return str(v)


def _guess_level_from_text(msg: str) -> str:
    m = (msg or "").upper()
    if m.startswith("[E-") or "ERROR" in m:
        return "error"
    if m.startswith("[W-") or "WARN" in m:
        return "warning"
    if m.startswith("[I-") or "INFO" in m:
        return "info"
    return ""


def _pick_stem(em_v6: Optional[Mapping[str, Any]], default: Optional[str]) -> str:
    if default:
        return _sanitize_filename(default)
    if isinstance(em_v6, Mapping):
        project = em_v6.get("project") or {}
        run = project.get("run") or {}
        name = run.get("RunTitle") or project.get("ProjectName") or "em_v6"
        return _sanitize_filename(str(name)) + "_diagnostics"
    return f"em_v6_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-]+", "_", name.strip())


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------

def _render_save_controls(
    raw_payload: List[Any],
    df: pd.DataFrame,
    em_v6: Optional[Mapping[str, Any]],
    filename_stem: str,
) -> None:
    st.subheader("Save diagnostics")

    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 2])
    with c1:
        want_csv = st.checkbox("CSV", value=True)
    with c2:
        want_json = st.checkbox("JSON", value=False)
    with c3:
        want_ndjson = st.checkbox("NDJSON", value=False)
    with c4:
        include_model = st.checkbox("Include EMJSON in ZIP", value=False)

    # Individual downloads
    if want_csv:
        st.download_button(
            label="Download CSV",
            data=_to_csv_bytes(df),
            file_name=f"{filename_stem}.csv",
            mime="text/csv",
        )
    if want_json:
        st.download_button(
            label="Download JSON",
            data=_to_json_bytes(df),
            file_name=f"{filename_stem}.json",
            mime="application/json",
        )
    if want_ndjson:
        st.download_button(
            label="Download NDJSON",
            data=_to_ndjson_bytes(df),
            file_name=f"{filename_stem}.ndjson",
            mime="application/x-ndjson",
        )

    # ZIP bundle (lossless)
    zip_bytes = _to_zip_bytes(
        filtered_df=df,
        raw_payload=raw_payload,
        base=filename_stem,
        include_csv=want_csv,
        include_json=want_json,
        include_ndjson=want_ndjson,
        em_v6=em_v6 if include_model else None,
    )
    st.download_button(
        label="Download ZIP bundle",
        data=zip_bytes,
        file_name=f"{filename_stem}.zip",
        mime="application/zip",
        help="Contains diagnostics_raw.json (verbatim), selected normalized formats, and optionally model_em_v6.json.",
    )


def _to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def _to_json_bytes(df: pd.DataFrame) -> bytes:
    records = df.to_dict(orient="records")
    return json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8")


def _to_ndjson_bytes(df: pd.DataFrame) -> bytes:
    out = io.StringIO()
    for rec in df.to_dict(orient="records"):
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out.getvalue().encode("utf-8")


def _to_zip_bytes(
    *,
    filtered_df: pd.DataFrame,
    raw_payload: List[Any],
    base: str,
    include_csv: bool,
    include_json: bool,
    include_ndjson: bool,
    em_v6: Optional[Mapping[str, Any]] = None,
) -> bytes:
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Raw diagnostics
        zf.writestr(f"{base}/diagnostics_raw.json", json.dumps(raw_payload, ensure_ascii=False, indent=2))
        if include_csv:
            zf.writestr(f"{base}/{base}.csv", _to_csv_bytes(filtered_df))
        if include_json:
            zf.writestr(f"{base}/{base}.json", _to_json_bytes(filtered_df))
        if include_ndjson:
            zf.writestr(f"{base}/{base}.ndjson", _to_ndjson_bytes(filtered_df))
        if em_v6 is not None:
            zf.writestr(f"{base}/model_em_v6.json", json.dumps(em_v6, ensure_ascii=False, indent=2))
        zf.writestr(
            f"{base}/README.txt",
            (
                f"{base}\n"
                f"Exported: {datetime.now().isoformat(timespec='seconds')}\n"
                "Contents:\n"
                "  - diagnostics_raw.json (verbatim payload)\n"
                "  - CSV / JSON / NDJSON (normalized, filtered)\n"
                "  - model_em_v6.json (optional)\n"
            ),
        )
    mem.seek(0)
    return mem.read()
