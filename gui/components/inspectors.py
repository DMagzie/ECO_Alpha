# explorer_gui/inspectors.py
from __future__ import annotations
from pathlib import Path
from typing import Any, List, Tuple
import sys, json
import xml.etree.ElementTree as ET

# Streamlit optional
try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore

# Ensure root on path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Core helpers
from em_core import (
    get_active_model,
    ensure_cz_canonical,
    normalize_model,
    coverage_report,
)

# -------- constants to guard heavy rendering ----------
MAX_CODE_CHARS = 300_000   # switch to text_area above this to avoid JS RangeError
MAX_SEARCH_RESULTS = 200

# ---------- utils ----------
def _pretty_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        try:
            return json.dumps(json.loads(str(obj)), ensure_ascii=False, indent=2)
        except Exception:
            return str(obj)

def _pretty_xml(xml_text: str) -> str:
    try:
        root = ET.fromstring(xml_text)
        try:
            ET.indent(root, space="  ", level=0)  # 3.9+
        except Exception:
            pass
        return ET.tostring(root, encoding="unicode")
    except Exception:
        try:
            import xml.dom.minidom as minidom
            return minidom.parseString(xml_text).toprettyxml(indent="  ")
        except Exception:
            return xml_text

def _json_find_paths(obj: Any, needle: str, limit: int = MAX_SEARCH_RESULTS) -> List[str]:
    if not needle:
        return []
    needle = needle.lower()
    results: List[str] = []

    def walk(o: Any, path: str):
        nonlocal results
        if len(results) >= limit:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                kp = f"{path}.{k}" if path else k
                # check key/value
                if needle in str(k).lower() or (isinstance(v, (str, int, float)) and needle in str(v).lower()):
                    results.append(kp)
                    if len(results) >= limit:
                        return
                walk(v, kp)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                ip = f"{path}[{i}]"
                if isinstance(v, (str, int, float)) and needle in str(v).lower():
                    results.append(ip)
                    if len(results) >= limit:
                        return
                walk(v, ip)

    walk(obj, "")
    return results

def _xml_find_lines(xml_text: str, needle: str, limit: int = MAX_SEARCH_RESULTS) -> List[Tuple[int, str]]:
    if not needle:
        return []
    n = needle.lower()
    hits: List[Tuple[int, str]] = []
    for i, line in enumerate(xml_text.splitlines(), 1):
        if n in line.lower():
            hits.append((i, line.strip()))
            if len(hits) >= limit:
                break
    return hits

def _xml_basic_metrics(xml_text: str) -> dict:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return {"parsed": False}
    b = root.find(".//Building")
    cz = (b is not None) and (b.attrib.get("ClimateZone") or b.attrib.get("climateZone"))
    spaces = root.findall(".//Spaces/Space")
    return {
        "parsed": True,
        "root_tag": root.tag,
        "has_building": b is not None,
        "climate_zone": cz or "",
        "spaces": len(spaces),
    }

# ---------- inspectors ----------
def render_emjson_inspector() -> None:
    if st is None:
        return

    st.subheader("EMJSON Inspector")

    # Use the *normalized* active model (what exporter/validator actually sees)
    m = get_active_model()
    m = ensure_cz_canonical(m)
    mn = normalize_model(m)

    proj = (mn.get("project") or {})
    name = proj.get("name") or "(no name)"
    cz = mn.get("climate_zone") or "(missing)"
    zones = mn.get("zones") or []

    st.write(f"**Project:** {name}  •  **Climate Zone:** {cz}  •  **Zones:** {len(zones)}")

    with st.expander("Coverage report", expanded=True):
        for line in coverage_report(mn):
            st.write("•", line)

    # Quick search
    q = st.text_input("Search keys/values in EMJSON")
    if q:
        hits = _json_find_paths(mn, q, limit=MAX_SEARCH_RESULTS)
        if hits:
            st.success(f"Found {len(hits)} path(s). Showing up to {MAX_SEARCH_RESULTS}.")
            for p in hits:
                st.code(p)
        else:
            st.info("No matches.")

    # Interactive JSON viewer (safe for very large dicts)
    with st.expander("View EMJSON (normalized)", expanded=False):
        # st.json is safer than st.code for huge dicts (no Prism recursion)
        st.json(mn, expanded=False)

        # Optional raw text toggle for copy/paste
        if st.checkbox("Show raw JSON text (may be large)", key="emjson_raw_toggle"):
            txt = _pretty_json(mn)
            # Avoid st.code for massive strings to prevent JS RangeError
            if len(txt) > MAX_CODE_CHARS:
                st.text_area("Raw JSON", value=txt, height=300)
            else:
                st.code(txt, language="json")

    st.download_button(
        "Download EMJSON",
        data=_pretty_json(mn).encode("utf-8"),
        file_name=f"{(name or 'Model').replace(' ', '_')}.emjson.json",
        mime="application/json",
    )

    # Inspect another EMJSON without replacing active model
    with st.expander("Upload an EMJSON to inspect (does not replace active model)", expanded=False):
        up = st.file_uploader("Choose .json", type=["json"], key="inspect_emjson_uploader")
        if up is not None:
            try:
                tmp = json.loads(up.getvalue().decode("utf-8"))
                tmp_n = normalize_model(ensure_cz_canonical(tmp))
                st.write(f"Zones: {len(tmp_n.get('zones') or [])} • CZ: {tmp_n.get('climate_zone') or '(missing)'}")
                st.json(tmp_n, expanded=False)
            except Exception as e:
                st.error(f"Failed to parse: {e}")

def render_xml_inspector() -> None:
    if st is None:
        return

    st.subheader("XML (CBECC / SDDXML) Inspector")
    xml_text = st.session_state.get("source_xml_text")
    xml_name = st.session_state.get("source_xml_name") or "source.xml"

    # Allow ad-hoc XML inspection without affecting the import flow
    with st.expander("Load XML for inspection (optional, does not replace imported XML)", expanded=False):
        up = st.file_uploader(
            "Inspect XML",
            type=["xml", "cbid22x", "cibd22x", "sddxml"],
            key="inspect_xml_uploader",
        )
        if up is not None:
            try:
                raw = up.getvalue()
                if not raw.lstrip().startswith((b"<", b"<?xml")):
                    st.error("File does not look like XML.")
                else:
                    xml_text = raw.decode("utf-8", errors="ignore")
                    xml_name = up.name or "inspect.xml"
            except Exception as e:
                st.error(f"Failed to read: {e}")

    if not isinstance(xml_text, str) or not xml_text.strip():
        st.info("No source XML available yet. Import a CBECC/SDDXML file in the **CBECC Import** tab.")
        return

    m = _xml_basic_metrics(xml_text)
    if not m.get("parsed"):
        st.error("XML failed to parse. Showing raw content below.")
        pretty = xml_text
    else:
        st.write(
            f"**Root:** {m['root_tag']}  •  **Building present:** {m['has_building']}  •  "
            f"**ClimateZone:** {m['climate_zone'] or '(missing)'}  •  **Spaces:** {m['spaces']}"
        )
        pretty = _pretty_xml(xml_text)

    # Search
    q = st.text_input("Search text in XML")
    if q:
        hits = _xml_find_lines(pretty, q, limit=MAX_SEARCH_RESULTS)
        if hits:
            st.success(f"Found {len(hits)} line(s). Showing up to {MAX_SEARCH_RESULTS}.")
            for ln, tx in hits:
                st.write(f"{ln}: {tx}")
        else:
            st.info("No matches.")

    # Large-content guard for XML view
    with st.expander("View XML", expanded=False):
        if len(pretty) > MAX_CODE_CHARS:
            st.text_area("XML (large file rendered as plain text)", value=pretty, height=300)
        else:
            st.code(pretty, language="xml")

    st.download_button(
        "Download XML",
        data=pretty.encode("utf-8"),
        file_name=xml_name,
        mime="application/xml",
    )
