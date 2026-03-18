"""Chat API routes."""

import math
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from app.services.ai_service import chat_with_ai
from app.services.data_service import get_result_values_for_tests, get_values_for_test, query_tests
from app.db import get_database_overview


def sanitize_floats(obj):
    """Replace NaN/Infinity with None for JSON serialization."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_floats(v) for v in obj]
    return obj

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class CardApproval(BaseModel):
    approved: bool
    card_indices: list[int] = []  # which proposed cards to render


# In-memory conversation store (replace with Redis/DB for production)
conversations: dict[str, list[dict]] = {}


@router.post("/send")
async def send_message(req: ChatRequest):
    """Send a message to the AI and get a response."""
    conv_id = req.conversation_id or "default"

    # Get or create conversation history
    history = conversations.get(conv_id, [])

    # Add user message
    user_msg = [{"role": "user", "content": req.message}]

    try:
        result = await chat_with_ai(user_msg, conversation_history=history)

        # Update conversation history (keep last 20 turns to prevent token overflow)
        history.append({"role": "user", "content": req.message})
        history.append({"role": "assistant", "content": result["response"]})
        if len(history) > 40:
            history = history[-40:]
        conversations[conv_id] = history

        return JSONResponse(content=sanitize_floats({
            "response": result["response"],
            "tool_calls": result.get("tool_calls", []),
            "conversation_id": conv_id,
        }))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def database_overview():
    """Get database overview for initial greeting."""
    try:
        overview = await get_database_overview()
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_conversation(conversation_id: Optional[str] = "default"):
    """Reset a conversation."""
    if conversation_id in conversations:
        del conversations[conversation_id]
    return {"status": "ok"}


class ChartRequest(BaseModel):
    card_type: str  # stat_summary, distribution, time_series, stress_strain, comparison, trend, spc
    title: str
    metric: Optional[str] = None
    test_ids: list[str] = []
    result_name: Optional[str] = None
    unit_filter: Optional[str] = "Stress"
    spc_mode: Optional[str] = "std3"  # "std3" or "custom"
    ucl: Optional[float] = None
    lcl: Optional[float] = None


@router.post("/chart-data")
async def get_chart_data(req: ChartRequest):
    """Generate Plotly chart data for an approved card."""
    try:
        if req.card_type in ("stat_summary", "distribution", "trend"):
            # Fetch result values across tests
            if not req.result_name and req.metric:
                # Parse "Young's modulus, begin (Stress)" -> result_name="Young's modulus, begin", unit="Stress"
                parts = req.metric.rsplit("(", 1)
                req.result_name = parts[0].strip()
                if len(parts) > 1:
                    req.unit_filter = parts[1].rstrip(")")

            data = await get_result_values_for_tests(
                req.test_ids, req.result_name or "", req.unit_filter or "Stress"
            )

            results = data.get("results", [])
            if not results:
                return {"error": "No data found for this metric", "plotData": None}

            # Filter out NaN and None values
            valid_results = [r for r in results if isinstance(r.get("value"), (int, float)) and not math.isnan(r["value"])]
            if not valid_results:
                return {"error": "All values are NaN or missing", "plotData": None}

            values = [r["value"] for r in valid_results]
            labels = [r["test_name"] for r in valid_results]
            unit = valid_results[0].get("unit", "") if valid_results else ""

            # Unit conversion: Pa → MPa for Stress, Pa → GPa for modulus
            display_unit = unit
            if unit == "Stress":
                is_modulus = "modulus" in (req.result_name or "").lower()
                if is_modulus:
                    values = [v / 1e9 for v in values]
                    display_unit = "GPa"
                else:
                    values = [v / 1e6 for v in values]
                    display_unit = "MPa"
            elif unit == "Ratio":
                values = [v * 100 for v in values]
                display_unit = "%"

            if req.card_type == "stat_summary":
                import numpy as np
                arr = np.array(values)
                return {
                    "plotData": {
                        "data": [{
                            "type": "bar",
                            "x": labels,
                            "y": values,
                            "marker": {"color": "#E3000B"},
                        }],
                        "layout": {
                            "yaxis": {"title": {"text": f"{req.result_name} ({display_unit})", "standoff": 15}},
                            "xaxis": {"title": "Specimen", "tickangle": -45},
                        },
                    },
                    "stats": {
                        "mean": float(np.mean(arr)),
                        "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0,
                        "min": float(np.min(arr)),
                        "max": float(np.max(arr)),
                        "count": len(arr),
                    },
                }

            elif req.card_type == "distribution":
                return {
                    "plotData": {
                        "data": [{
                            "type": "histogram",
                            "x": values,
                            "marker": {"color": "#E3000B"},
                            "nbinsx": max(5, len(values) // 3),
                        }],
                        "layout": {
                            "xaxis": {"title": f"{req.result_name} ({display_unit})"},
                            "yaxis": {"title": {"text": "Count", "standoff": 15}},
                        },
                    },
                }

            elif req.card_type == "trend":
                dates = [r.get("date", "") for r in valid_results]
                return {
                    "plotData": {
                        "data": [{
                            "type": "scatter",
                            "x": dates if any(dates) else list(range(len(values))),
                            "y": values,
                            "mode": "lines+markers",
                            "marker": {"color": "#E3000B"},
                        }],
                        "layout": {
                            "yaxis": {"title": {"text": f"{req.result_name} ({display_unit})", "standoff": 15}},
                            "xaxis": {"title": "Date" if any(dates) else "Test Index"},
                        },
                    },
                }

        elif req.card_type == "spc":
            # SPC Control Chart
            if not req.result_name and req.metric:
                parts = req.metric.rsplit("(", 1)
                req.result_name = parts[0].strip()
                if len(parts) > 1:
                    req.unit_filter = parts[1].rstrip(")")

            data = await get_result_values_for_tests(
                req.test_ids, req.result_name or "", req.unit_filter or "Stress"
            )

            results = data.get("results", [])
            if not results:
                return {"error": "No data found for this metric", "plotData": None}

            import numpy as np

            valid_results = [r for r in results if isinstance(r.get("value"), (int, float)) and not math.isnan(r["value"])]
            if not valid_results:
                return {"error": "All values are NaN or missing", "plotData": None}

            # Sort by date then specimen name for sequential SPC ordering
            valid_results.sort(key=lambda r: (r.get("date", ""), r.get("test_name", "")))
            # Deduplicate — keep first value per specimen
            seen = set()
            deduped = []
            for r in valid_results:
                if r["test_name"] not in seen:
                    seen.add(r["test_name"])
                    deduped.append(r)
            valid_results = deduped

            values = [r["value"] for r in valid_results]
            labels = [r["test_name"] for r in valid_results]
            unit = valid_results[0].get("unit", "") if valid_results else ""

            # Unit conversion
            display_unit = unit
            if unit == "Stress":
                is_modulus = "modulus" in (req.result_name or "").lower()
                if is_modulus:
                    values = [v / 1e9 for v in values]
                    display_unit = "GPa"
                else:
                    values = [v / 1e6 for v in values]
                    display_unit = "MPa"
            elif unit == "Ratio":
                values = [v * 100 for v in values]
                display_unit = "%"

            arr = np.array(values)
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0

            if req.spc_mode == "custom" and req.ucl is not None and req.lcl is not None:
                ucl = req.ucl
                lcl = req.lcl
            else:
                ucl = mean_val + 3 * std_val
                lcl = mean_val - 3 * std_val

            # Identify out-of-control points
            ooc_x = [labels[i] for i, v in enumerate(values) if v > ucl or v < lcl]
            ooc_y = [v for v in values if v > ucl or v < lcl]

            traces = [
                {
                    "type": "scatter",
                    "x": labels,
                    "y": values,
                    "mode": "lines+markers",
                    "name": "Measurements",
                    "marker": {"color": "#E3000B", "size": 6},
                    "line": {"color": "#E3000B"},
                },
            ]

            # Out-of-control points highlighted
            if ooc_x:
                traces.append({
                    "type": "scatter",
                    "x": ooc_x,
                    "y": ooc_y,
                    "mode": "markers",
                    "name": "Out of control",
                    "marker": {"color": "#ef4444", "size": 10, "symbol": "diamond"},
                })

            is_std3 = req.spc_mode != "custom"

            shapes = [
                # Mean line (always shown)
                {"type": "line", "xref": "paper", "x0": 0, "x1": 1, "y0": mean_val, "y1": mean_val,
                 "line": {"color": "#10b981", "width": 2}},
            ]

            annotations = [
                {"xref": "paper", "x": 1.02, "y": mean_val, "text": f"Mean: {mean_val:.2f}", "showarrow": False,
                 "font": {"color": "#10b981", "size": 10}, "bgcolor": "white", "borderpad": 2},
            ]

            if is_std3:
                # ±3σ shaded zones
                shapes.extend([
                    {"type": "rect", "xref": "paper", "x0": 0, "x1": 1,
                     "y0": mean_val - 3 * std_val, "y1": mean_val + 3 * std_val,
                     "fillcolor": "rgba(239,68,68,0.05)", "line": {"width": 0}, "layer": "below"},
                    {"type": "rect", "xref": "paper", "x0": 0, "x1": 1,
                     "y0": mean_val - 2 * std_val, "y1": mean_val + 2 * std_val,
                     "fillcolor": "rgba(251,146,60,0.07)", "line": {"width": 0}, "layer": "below"},
                    {"type": "rect", "xref": "paper", "x0": 0, "x1": 1,
                     "y0": mean_val - 1 * std_val, "y1": mean_val + 1 * std_val,
                     "fillcolor": "rgba(16,185,129,0.08)", "line": {"width": 0}, "layer": "below"},
                    # ±3σ boundary lines
                    {"type": "line", "xref": "paper", "x0": 0, "x1": 1,
                     "y0": mean_val + 3 * std_val, "y1": mean_val + 3 * std_val,
                     "line": {"color": "#ef4444", "width": 1, "dash": "dot"}},
                    {"type": "line", "xref": "paper", "x0": 0, "x1": 1,
                     "y0": mean_val - 3 * std_val, "y1": mean_val - 3 * std_val,
                     "line": {"color": "#ef4444", "width": 1, "dash": "dot"}},
                ])
                annotations.extend([
                    {"xref": "paper", "x": 1.02, "y": mean_val + 3 * std_val, "text": "+3σ", "showarrow": False,
                     "font": {"color": "#ef4444", "size": 9}, "bgcolor": "white", "borderpad": 2},
                    {"xref": "paper", "x": 1.02, "y": mean_val - 3 * std_val, "text": "-3σ", "showarrow": False,
                     "font": {"color": "#ef4444", "size": 9}, "bgcolor": "white", "borderpad": 2},
                    {"xref": "paper", "x": 1.02, "y": mean_val + 2 * std_val, "text": "+2σ", "showarrow": False,
                     "font": {"color": "#fb923c", "size": 9}, "bgcolor": "white", "borderpad": 2},
                    {"xref": "paper", "x": 1.02, "y": mean_val - 2 * std_val, "text": "-2σ", "showarrow": False,
                     "font": {"color": "#fb923c", "size": 9}, "bgcolor": "white", "borderpad": 2},
                    {"xref": "paper", "x": 1.02, "y": mean_val + 1 * std_val, "text": "+1σ", "showarrow": False,
                     "font": {"color": "#10b981", "size": 9}, "bgcolor": "white", "borderpad": 2},
                    {"xref": "paper", "x": 1.02, "y": mean_val - 1 * std_val, "text": "-1σ", "showarrow": False,
                     "font": {"color": "#10b981", "size": 9}, "bgcolor": "white", "borderpad": 2},
                ])
            else:
                # Custom UCL/LCL — show only the two limit lines
                shapes.extend([
                    {"type": "line", "xref": "paper", "x0": 0, "x1": 1, "y0": ucl, "y1": ucl,
                     "line": {"color": "#ef4444", "width": 2, "dash": "dash"}},
                    {"type": "line", "xref": "paper", "x0": 0, "x1": 1, "y0": lcl, "y1": lcl,
                     "line": {"color": "#ef4444", "width": 2, "dash": "dash"}},
                ])
                annotations.extend([
                    {"xref": "paper", "x": 1.02, "y": ucl, "text": f"UCL: {ucl:.2f}", "showarrow": False,
                     "font": {"color": "#ef4444", "size": 10}, "bgcolor": "white", "borderpad": 2},
                    {"xref": "paper", "x": 1.02, "y": lcl, "text": f"LCL: {lcl:.2f}", "showarrow": False,
                     "font": {"color": "#ef4444", "size": 10}, "bgcolor": "white", "borderpad": 2},
                ])

            return sanitize_floats({
                "plotData": {
                    "data": traces,
                    "layout": {
                        "yaxis": {"title": {"text": f"{req.result_name} ({display_unit})", "standoff": 15}},
                        "xaxis": {"title": "Specimen", "tickangle": -45},
                        "shapes": shapes,
                        "annotations": annotations,
                    },
                },
                "stats": {
                    "mean": mean_val,
                    "std": std_val,
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                    "count": len(arr),
                    "ucl": ucl,
                    "lcl": lcl,
                    "ooc_count": len(ooc_x),
                },
                "subtitle": f"SPC: {len(ooc_x)} of {len(values)} out of control" if ooc_x else f"SPC: All {len(values)} specimens within control limits",
            })

        elif req.card_type == "stress_strain" and req.test_ids:
            from app.db import tests_collection, values_collection

            # First: find which tests actually have value data
            pipeline = [
                {"$match": {"metadata.refId": {"$in": req.test_ids}}},
                {"$group": {"_id": "$metadata.refId"}},
            ]
            ids_with_data = set()
            async for doc in values_collection.aggregate(pipeline):
                ids_with_data.add(doc["_id"])

            test_ids_with_data = [tid for tid in req.test_ids if tid in ids_with_data]

            if not test_ids_with_data:
                return {"error": f"None of the {len(req.test_ids)} tests have measurement data", "plotData": None}

            traces = []
            skipped = 0
            colors = ["#E3000B", "#2563eb", "#16a34a", "#f59e0b", "#8b5cf6",
                       "#06b6d4", "#f97316", "#ec4899", "#14b8a6", "#84cc16",
                       "#6366f1", "#e879f9", "#22d3ee", "#fbbf24", "#a78bfa",
                       "#34d399", "#fb7185", "#38bdf8", "#c084fc", "#fcd34d"]

            for i, test_id in enumerate(test_ids_with_data):
                test = await tests_collection.find_one({"_id": test_id})
                if not test:
                    continue

                # Find the UUIDs for Standard force (Stress) and Strain/Deformation (Ratio)
                stress_uuid = None
                strain_uuid = None
                for vc in test.get("valueColumns", []):
                    vid = vc.get("_id", "")
                    name = (vc.get("name") or "").lower()
                    unit = (vc.get("unitTableId") or "").lower()
                    if "_Value" not in vid or vid.endswith("_Key"):
                        continue
                    if "standard force" in name and "stress" in unit and stress_uuid is None:
                        stress_uuid = vid.split("-Zwick")[0].strip("{}")
                    elif ("strain" in name or "deformation" in name) and "ratio" in unit and "plastic" not in name and "rate" not in name and "nominal" not in name and "transverse" not in name and strain_uuid is None:
                        strain_uuid = vid.split("-Zwick")[0].strip("{}")

                if not stress_uuid or not strain_uuid:
                    skipped += 1
                    continue

                # Fetch only the two channels we need
                force_doc = await values_collection.find_one({
                    "metadata.refId": test_id,
                    "metadata.childId": {"$regex": f"{stress_uuid}.*Stress"}
                })
                strain_doc = await values_collection.find_one({
                    "metadata.refId": test_id,
                    "metadata.childId": {"$regex": f"{strain_uuid}.*Ratio"}
                })

                if force_doc and strain_doc and force_doc.get("values") and strain_doc.get("values"):
                    force_vals = force_doc["values"]
                    strain_vals = strain_doc["values"]
                    n = min(len(force_vals), len(strain_vals))
                    step = max(1, n // 500)
                    specimen_name = test.get("name", f"Test {i+1}")
                    # Convert Pa to MPa for stress, raw ratio to % for strain
                    stress_mpa = [v / 1e6 for v in force_vals[:n:step]]
                    strain_pct = [v * 100 for v in strain_vals[:n:step]]
                    traces.append({
                        "type": "scatter",
                        "x": strain_pct,
                        "y": stress_mpa,
                        "mode": "lines",
                        "name": specimen_name,
                        "line": {"color": colors[i % len(colors)]},
                    })
                else:
                    skipped += 1

            if not traces:
                return {"error": f"Could not extract stress-strain data. {len(ids_with_data)} tests had raw data but channels didn't match.", "plotData": None}

            return {
                "plotData": {
                    "data": traces,
                    "layout": {
                        "xaxis": {"title": "Strain (%)"},
                        "yaxis": {"title": {"text": "Stress (MPa)", "standoff": 15}},
                        "legend": {"orientation": "h", "y": -0.2, "x": 0.5, "xanchor": "center"},
                        "hovermode": "closest",
                    },
                },
                "subtitle": f"{len(traces)} of {len(req.test_ids)} tests plotted",
                "info": f"{len(req.test_ids) - len(ids_with_data)} had no measurement data, {skipped} had missing channels.",
            }

        elif req.card_type == "table":
            return {"plotData": None, "message": "Table cards show raw data"}

        return {"error": f"Unsupported card type: {req.card_type}", "plotData": None}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
