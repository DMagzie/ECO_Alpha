## File 3: `parsers_catalogs.py` (COMPLETE REPLACEMENT)
from __future__ import annotations
from typing import Dict, Any, List, Optional
from xml.etree import ElementTree as ET


def _lt(tag: str) -> str:
    return tag.split('}', 1)[-1] if '}' in (tag or '') else (tag or '')


def _child_text_local(node: ET.Element | None, *names: str) -> str | None:
    if node is None:
        return None
    wanted = {n.lower() for n in names}
    for ch in list(node):
        if _lt(getattr(ch, "tag", "")).lower() in wanted:
            txt = (ch.text or "").strip()
            if txt:
                return txt
    return None


def _to_float(s: str | None) -> float | None:
    if not s: return None
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return None


def _diag(em: Dict[str, Any], level: str, code: str, message: str, context: Dict[str, Any] | None = None):
    em.setdefault("diagnostics", []).append({
        "level": level, "code": code, "message": message, "context": context or {}
    })


def parse_location(root: ET.Element, em: Dict[str, Any]) -> Dict[str, Any]:
    """Parse project location information."""
    info = {}
    proj = (root.find(".//ProjectInfo") or root.find(".//Info") or root.find(".//Project"))
    if proj is not None:
        bldg_az = (_child_text_local(proj, "BldgAz") or _child_text_local(proj, "BuildingAzimuth")
                   or proj.get("BldgAz") or proj.get("BuildingAzimuth"))
        try:
            info["building_azimuth_deg"] = float(bldg_az) if bldg_az else None
        except Exception:
            pass

        site = (proj.find(".//Site") or proj.find(".//Location"))
        if site is not None:
            city = _child_text_local(site, "City") or site.get("City")
            state = _child_text_local(site, "State") or site.get("State")
            county = _child_text_local(site, "County") or site.get("County")
            climate = _child_text_local(site, "ClimateZone") or _child_text_local(site, "CZ") or site.get(
                "ClimateZone") or site.get("CZ")
            zip_code = _child_text_local(site, "ZipCode") or _child_text_local(site, "Zip") or site.get(
                "ZipCode") or site.get("Zip")
            weather = _child_text_local(site, "WeatherFile") or _child_text_local(site, "Weather") or site.get(
                "WeatherFile") or site.get("Weather")
            elev = _to_float(_child_text_local(site, "Elevation") or site.get("Elevation"))

            if city: info["city"] = city
            if state: info["state"] = state
            if county: info["county"] = county
            if climate: info["climate_zone"] = climate
            if zip_code: info["zip"] = zip_code
            if weather: info["weather_file"] = weather
            if elev is not None: info[
                "elevation_m"] = elev * 0.3048 if elev < 1000 else elev  # Convert ft to m if < 1000

    em.setdefault("project", {}).setdefault("location", {}).update({k: v for k, v in info.items() if v is not None})

    if info:
        _diag(em, "info", "I-LOCATION-PARSED",
              f"Location parsed: {info.get('city', 'N/A')}, {info.get('state', 'N/A')}")

    return em["project"]["location"]


def parse_du_types(
        root: ET.Element,
        em: Dict[str, Any],
        id_registry: Any = None  # IDRegistry instance (optional for catalogs)
) -> List[Dict[str, Any]]:
    """Parse dwelling unit type catalog."""
    out: List[Dict[str, Any]] = []

    for du in root.findall(".//DUType") + root.findall(".//DwellUnitType") + root.findall(".//DwellingUnitType"):
        name = _child_text_local(du, "Name") or du.get("Name") or du.get("id") or "DU"

        # Generate stable ID
        if id_registry:
            du_id = id_registry.generate_id("DU", name, context="", source_format="CIBD22X")
        else:
            du_id = du.get("id") or f"du:{name.lower().replace(' ', '_')}"

        item = {"id": du_id, "name": name}

        # Parse floor area (convert ft² to m²)
        fa_ft2 = _to_float(_child_text_local(du, "FloorArea") or _child_text_local(du, "Area")
                           or du.get("FloorArea") or du.get("Area"))
        if fa_ft2 is not None:
            item["floor_area_m2"] = fa_ft2 * 0.092903

        # Parse occupants
        occ = _to_float(_child_text_local(du, "Occupants") or _child_text_local(du, "NumOccupants")
                        or du.get("Occupants") or du.get("NumOccupants"))
        if occ is not None:
            item["occupants"] = int(occ)

        # Parse bedrooms
        beds = _to_float(_child_text_local(du, "Bedrooms") or _child_text_local(du, "NumBedrooms")
                         or du.get("Bedrooms") or du.get("NumBedrooms"))
        if beds is not None:
            item["bedrooms"] = int(beds)

        # Store annotation
        item["annotation"] = {
            "xml_tag": _lt(du.tag),
            "source_id": du.get("id"),
            "source_area_units": "ft2" if fa_ft2 is not None else None
        }

        out.append(item)

    em.setdefault("catalogs", {})["du_types"] = out

    if out:
        _diag(em, "info", "I-DU-TYPES-PARSED", f"Parsed {len(out)} dwelling unit types")

    return out


def parse_window_types(
        root: ET.Element,
        em: Dict[str, Any],
        id_registry: Any = None  # IDRegistry instance (optional)
) -> List[Dict[str, Any]]:
    """Parse window type catalog with fenestration properties."""
    out: List[Dict[str, Any]] = []

    for wt in root.findall(".//WindowType") + root.findall(".//FenestrationConstruction"):
        name = _child_text_local(wt, "Name") or wt.get("Name") or wt.get("id") or "WindowType"

        # Generate stable ID
        if id_registry:
            win_id = id_registry.generate_id("WIN", name, context="", source_format="CIBD22X")
        else:
            win_id = wt.get("id") or f"win:{name.lower().replace(' ', '_')}"

        item = {"id": win_id, "name": name}

        # Parse U-factor (convert Btu/h·ft²·°F to W/m²·K)
        uf_ip = _to_float(_child_text_local(wt, "UFactor") or _child_text_local(wt, "UValue")
                          or wt.get("UFactor") or wt.get("UValue"))
        if uf_ip is not None:
            item["u_factor_SI"] = uf_ip * 5.678263

        # Parse SHGC (dimensionless)
        shgc = _to_float(_child_text_local(wt, "SHGC") or _child_text_local(wt, "SolarHeatGainCoeff")
                         or wt.get("SHGC") or wt.get("SolarHeatGainCoeff"))
        if shgc is not None:
            item["shgc"] = shgc

        # Parse VT (dimensionless)
        vt = _to_float(_child_text_local(wt, "VT") or _child_text_local(wt, "VisibleTransmittance")
                       or wt.get("VT") or wt.get("VisibleTransmittance"))
        if vt is not None:
            item["vt"] = vt

        # Parse frame type
        frame = _child_text_local(wt, "FrameType") or _child_text_local(wt, "Frame") or wt.get("FrameType") or wt.get(
            "Frame")
        if frame:
            item["frame_type"] = frame

        # Parse glazing layers
        layers = _to_float(_child_text_local(wt, "GlazingLayers") or _child_text_local(wt, "NumPanes")
                           or wt.get("GlazingLayers") or wt.get("NumPanes"))
        if layers is not None:
            item["glazing_layers"] = int(layers)

        # Parse gas fill
        gas = _child_text_local(wt, "GasFill") or _child_text_local(wt, "Gas") or wt.get("GasFill") or wt.get("Gas")
        if gas:
            item["gas_fill"] = gas

        # Store annotation
        item["annotation"] = {
            "xml_tag": _lt(wt.tag),
            "source_id": wt.get("id"),
            "source_u_factor_units": "Btu/h-ft2-F" if uf_ip is not None else None
        }

        out.append(item)

    em.setdefault("catalogs", {})["window_types"] = out

    if out:
        _diag(em, "info", "I-WINDOW-TYPES-PARSED", f"Parsed {len(out)} window types")

    return out


def parse_construction_types(
        root: ET.Element,
        em: Dict[str, Any],
        id_registry: Any = None  # IDRegistry instance (optional)
) -> List[Dict[str, Any]]:
    """Parse construction assembly catalog."""
    out: List[Dict[str, Any]] = []

    for ct in root.findall(".//ConstructionType") + root.findall(".//Construction") + root.findall(
            ".//ConstructionAssembly"):
        name = _child_text_local(ct, "Name") or ct.get("Name") or ct.get("id") or "Construction"

        # Generate stable ID
        if id_registry:
            const_id = id_registry.generate_id("CONST", name, context="", source_format="CIBD22X")
        else:
            const_id = ct.get("id") or f"const:{name.lower().replace(' ', '_')}"

        item = {"id": const_id, "name": name}

        # Parse application
        apply_to = _child_text_local(ct, "ApplyTo") or _child_text_local(ct, "Type") or ct.get("ApplyTo") or ct.get(
            "Type")
        if apply_to:
            item["apply_to"] = apply_to.lower()

        # Parse U-value (convert Btu/h·ft²·°F to W/m²·K)
        uval_ip = _to_float(_child_text_local(ct, "UValue") or _child_text_local(ct, "UFactor")
                            or ct.get("UValue") or ct.get("UFactor"))
        if uval_ip is not None:
            item["u_value_SI"] = uval_ip * 5.678263

        # Parse R-value (convert h·ft²·°F/Btu to m²·K/W)
        rval_ip = _to_float(_child_text_local(ct, "RValue") or _child_text_local(ct, "Resistance")
                            or ct.get("RValue") or ct.get("Resistance"))
        if rval_ip is not None:
            item["r_value_SI"] = rval_ip * 0.176110

        # Parse layers (simplified)
        layers = []
        for layer in ct.findall(".//Layer") + ct.findall(".//Material"):
            layer_name = _child_text_local(layer, "Name") or layer.get("Name") or "Layer"
            thickness_in = _to_float(_child_text_local(layer, "Thickness") or layer.get("Thickness"))

            layer_data = {"name": layer_name}
            if thickness_in is not None:
                layer_data["thickness_m"] = thickness_in * 0.0254  # inches to meters

            layers.append(layer_data)

        if layers:
            item["layers"] = layers

        # Store annotation
        item["annotation"] = {
            "xml_tag": _lt(ct.tag),
            "source_id": ct.get("id"),
            "source_u_value_units": "Btu/h-ft2-F" if uval_ip is not None else None,
            "source_r_value_units": "h-ft2-F/Btu" if rval_ip is not None else None
        }

        out.append(item)

    em.setdefault("catalogs", {})["construction_types"] = out

    if out:
        _diag(em, "info", "I-CONSTRUCTION-TYPES-PARSED", f"Parsed {len(out)} construction types")

    return out


def parse_pv(
        root: ET.Element,
        em: Dict[str, Any],
        id_registry: Any = None  # IDRegistry instance (optional)
) -> List[Dict[str, Any]]:
    """Parse photovoltaic system catalog."""
    out: List[Dict[str, Any]] = []

    for pv in root.findall(".//PV") + root.findall(".//Array") + root.findall(".//PVArray") + root.findall(
            ".//PhotovoltaicArray"):
        name = _child_text_local(pv, "Name") or pv.get("Name") or pv.get("id") or "PV"

        # Generate stable ID
        if id_registry:
            pv_id = id_registry.generate_id("PV", name, context="", source_format="CIBD22X")
        else:
            pv_id = pv.get("id") or f"pv:{name.lower().replace(' ', '_')}"

        item = {"id": pv_id, "name": name}

        # Parse DC capacity
        cap = _to_float(_child_text_local(pv, "CapacityKW") or _child_text_local(pv, "Capacity")
                        or _child_text_local(pv, "RatedPowerDC") or pv.get("CapacityKW") or pv.get("Capacity"))
        if cap is not None:
            item["dc_capacity_kW"] = cap

        # Parse tilt
        tilt = _to_float(_child_text_local(pv, "Tilt") or _child_text_local(pv, "TiltAngle")
                         or pv.get("Tilt") or pv.get("TiltAngle"))
        if tilt is not None:
            item["tilt_deg"] = tilt

        # Parse azimuth
        az = _to_float(_child_text_local(pv, "Azimuth") or _child_text_local(pv, "Az")
                       or pv.get("Azimuth") or pv.get("Az"))
        if az is not None:
            item["azimuth_deg"] = az

        # Parse array type
        array_type = _child_text_local(pv, "ArrayType") or _child_text_local(pv, "Type") or pv.get(
            "ArrayType") or pv.get("Type")
        if array_type:
            item["array_type"] = array_type

        # Parse module type
        module = _child_text_local(pv, "ModuleType") or _child_text_local(pv, "Module") or pv.get(
            "ModuleType") or pv.get("Module")
        if module:
            item["module_type"] = module

        # Parse inverter efficiency
        inv_eff = _to_float(_child_text_local(pv, "InverterEfficiency") or _child_text_local(pv, "InvEff")
                            or pv.get("InverterEfficiency") or pv.get("InvEff"))
        if inv_eff is not None:
            item["inverter_efficiency"] = inv_eff

        # Store annotation
        item["annotation"] = {
            "xml_tag": _lt(pv.tag),
            "source_id": pv.get("id")
        }

        out.append(item)

    em.setdefault("systems", {})["pv"] = out

    if out:
        _diag(em, "info", "I-PV-PARSED", f"Parsed {len(out)} PV arrays")

    return out



