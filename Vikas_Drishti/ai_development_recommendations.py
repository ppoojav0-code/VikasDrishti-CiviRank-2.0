"""AI photo assessment, same-photo future visualisation and indicative budget.

Configure OPENAI_API_KEY in .streamlit/secrets.toml or the environment.
Vision uses gpt-4.1-mini by default; image editing uses gpt-image-1 by default.
"""
import base64
import hashlib
import io
import json
import os
import re

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

# Standard default rates and units for common slum redevelopment infrastructure
INTERVENTION_METADATA = {
    "Road resurfacing": {
        "category": "Roads & Transportation",
        "rate": 1200,
        "unit": "sq. metre",
        "default_qty": 1000,
        "default_priority": "High",
        "reason": "Provide durable paved road surface for safe vehicular access and emergency services.",
    },
    "Covered drainage": {
        "category": "Drainage & Sewerage",
        "rate": 8500,
        "unit": "running metre",
        "default_qty": 250,
        "default_priority": "Critical",
        "reason": "Prevent standing wastewater, vector-borne diseases, and monsoon waterlogging.",
    },
    "Street lights": {
        "category": "Electrification & Safety",
        "rate": 28000,
        "unit": "unit",
        "default_qty": 25,
        "default_priority": "Medium",
        "reason": "Improve night-time visibility, resident security, and public safety.",
    },
    "Waste collection points": {
        "category": "Solid Waste Management",
        "rate": 45000,
        "unit": "unit",
        "default_qty": 8,
        "default_priority": "High",
        "reason": "Eliminate open garbage dumping, improve public hygiene, and facilitate door-to-door collection.",
    },
    "Pedestrian pathway": {
        "category": "Pedestrian Infrastructure",
        "rate": 2200,
        "unit": "sq. metre",
        "default_qty": 500,
        "default_priority": "Medium",
        "reason": "Ensure all-weather, well-graded walkways segregated from motor traffic for residents and children.",
    },
    "Community water points": {
        "category": "Water Supply",
        "rate": 180000,
        "unit": "unit",
        "default_qty": 3,
        "default_priority": "Critical",
        "reason": "Guarantee safe, potable piped drinking water access within short walking distance.",
    },
    "Parks and public spaces": {
        "category": "Environment & Green Spaces",
        "rate": 900,
        "unit": "sq. metre",
        "default_qty": 300,
        "default_priority": "Low",
        "reason": "Create open green spaces, shade trees, and safe community gathering areas.",
    },
    "Toilet / sanitation block": {
        "category": "Sanitation & Hygiene",
        "rate": 1800000,
        "unit": "unit",
        "default_qty": 1,
        "default_priority": "Critical",
        "reason": "Eliminate open defecation and provide well-maintained community toilet and hygiene facilities.",
    },
    "Housing facade & structural upgrade": {
        "category": "Housing & Shelter",
        "rate": 350000,
        "unit": "unit",
        "default_qty": 10,
        "default_priority": "High",
        "reason": "Improve structural safety, weatherproofing, ventilation, and durable wall/roof finishes.",
    },
}


def _setting(name, default=""):
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, default) or "").strip()


def _api_key():
    # A key entered on the AI page takes precedence and is kept only in this session.
    return str(st.session_state.get("ai_openai_api_key", "") or _setting("OPENAI_API_KEY")).strip()


def _image_bytes(uploaded_image):
    """Normalise uploaded PNG/JPEG to a clean, EXIF-correct JPEG/PNG for APIs."""
    try:
        uploaded_image.seek(0)
        image = ImageOps.exif_transpose(Image.open(uploaded_image)).convert("RGB")
        image.thumbnail((2048, 2048))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90, optimize=True)
        raw = buffer.getvalue()
        if len(raw) > 20 * 1024 * 1024:
            raise RuntimeError("Image is too large after compression. Please upload a smaller photo.")
        return image, raw
    except RuntimeError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise RuntimeError("The uploaded file is not a valid JPG or PNG image.") from exc


def _clean_json_response(content):
    """Strip code fences or surrounding text if present to parse JSON safely."""
    content = content.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if match:
        content = match.group(1).strip()
    return content


def _analyze_site(client, raw, area):
    """Ask vision model for deep, evidence-based visible observations and practical improvements."""
    data_url = "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    location_text = f" in {area}" if area else ""
    prompt = f"""You are a Senior Civil and Municipal Infrastructure Engineer and Computer Vision Specialist inspecting an actual photograph of an underdeveloped area / urban informal settlement{location_text} in India.

Carefully inspect and analyze the ACTUAL uploaded photograph.
Identify visible physical infrastructure problems, specifically checking for:
1. Damaged roads, unpaved surfaces, mud, potholes, lack of paving.
2. Open, overflowing, clogged, or unlined drainage ditches.
3. Garbage dumps, uncollected solid waste, plastic accumulation.
4. Poor, dilapidated, or temporary housing materials (corrugated tin, tarpaulin, broken brickwork).
5. Water supply shortages or lack of visible piped drinking water infrastructure.
6. Sanitation deficiencies, lack of community toilets, sewage runoff.
7. Missing streetlights or electrical safety hazards.
8. Unsafe, broken, or missing pedestrian walkways / footpaths.
9. Lack of greenery, tree cover, or organized public community spaces.

Return ONLY valid JSON using exactly this structure:
{{
  "identified_problems": [
    {{
      "category": "Roads / Drainage / Solid Waste / Housing / Water Supply / Sanitation / Lighting / Pedestrian / Greenery",
      "problem": "Brief name of the problem",
      "explanation": "Detailed explanation of where and what is visible in the photograph",
      "urgency": "Critical" | "High" | "Medium" | "Low"
    }}
  ],
  "recommendations": [
    {{
      "category": "Roads / Drainage / Solid Waste / Housing / Water Supply / Sanitation / Lighting / Pedestrian / Greenery",
      "action": "Practical physical infrastructure improvement",
      "priority": "Critical" | "High" | "Medium" | "Low",
      "impact": "Expected outcome on health, safety, or quality of life"
    }}
  ],
  "interventions": [
    "One or more exact names from: {', '.join(INTERVENTION_METADATA.keys())}"
  ],
  "design_prompt": "Specific visual editing instructions to transform this exact scene into a realistic, photorealistic improved neighbourhood. Must describe preserving the original camera viewpoint, building geometry, layout, and perspective while rendering covered drains, paved asphalt/concrete road, proper streetlights, clean surroundings, painted/improved building facades, and pleasant greenery."
}}

Ensure recommendations are derived directly from the visible photograph, not generic platitudes.
Provide 3-7 identified problems and 4-8 recommendations. Prioritize by urgency."""

    model = _setting("OPENAI_VISION_MODEL", "gpt-4.1-mini")
    response = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
            ],
        }],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The vision model returned an empty assessment. Please try again.")

    cleaned_content = _clean_json_response(content)
    try:
        result = json.loads(cleaned_content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"The vision model returned an unreadable assessment: {exc}") from exc

    # Validate and standardize identified_problems
    problems = result.get("identified_problems", [])
    standard_problems = []
    if isinstance(problems, list):
        for item in problems:
            if isinstance(item, dict):
                standard_problems.append({
                    "category": str(item.get("category", "General Infrastructure")).strip(),
                    "problem": str(item.get("problem", "Visible infrastructure issue")).strip(),
                    "explanation": str(item.get("explanation", "")).strip(),
                    "urgency": str(item.get("urgency", "High")).capitalize().strip(),
                })
            elif isinstance(item, str) and item.strip():
                standard_problems.append({
                    "category": "General Infrastructure",
                    "problem": item.strip(),
                    "explanation": item.strip(),
                    "urgency": "High",
                })
    result["identified_problems"] = standard_problems

    # Validate and standardize recommendations
    recommendations = result.get("recommendations", [])
    standard_recs = []
    if isinstance(recommendations, list):
        for item in recommendations:
            if isinstance(item, dict):
                standard_recs.append({
                    "category": str(item.get("category", "Infrastructure Improvement")).strip(),
                    "action": str(item.get("action", "Infrastructure upgrade")).strip(),
                    "priority": str(item.get("priority", "High")).capitalize().strip(),
                    "impact": str(item.get("impact", "Improves community livability")).strip(),
                })
            elif isinstance(item, str) and item.strip():
                standard_recs.append({
                    "category": "Infrastructure Improvement",
                    "action": item.strip(),
                    "priority": "High",
                    "impact": "Improves living standards",
                })
    result["recommendations"] = standard_recs

    # Keep only supported costed work items with reliable fallback
    raw_interventions = result.get("interventions", [])
    if isinstance(raw_interventions, list):
        selected_interventions = [
            item.strip() for item in raw_interventions if item.strip() in INTERVENTION_METADATA
        ]
    else:
        selected_interventions = []

    if not selected_interventions:
        # Infer based on identified problems or provide solid core set
        selected_interventions = [
            "Road resurfacing",
            "Covered drainage",
            "Street lights",
            "Waste collection points",
            "Pedestrian pathway",
        ]
    result["interventions"] = selected_interventions
    result["design_prompt"] = str(result.get("design_prompt", "")).strip()

    return result


def _generate_future_image(client, raw, area, analysis):
    """Edit the user's original photograph; preserve original viewpoint and layout."""
    problems_summary = "; ".join([
        f"{p.get('problem')}: {p.get('explanation')}"
        for p in analysis.get("identified_problems", [])[:5]
    ]) or "visible infrastructure gaps and unpaved roads"

    recs_summary = "; ".join([
        f"{r.get('action')}"
        for r in analysis.get("recommendations", [])[:6]
    ]) or "; ".join(analysis.get("interventions", []))

    location_text = f"Location context: {area}. " if area else ""
    design_guidance = analysis.get("design_prompt", "").strip()

    prompt = f"""{location_text}Perform a photorealistic architectural and municipal engineering IMAGE EDIT on this EXACT uploaded photograph.
CRITICAL MANDATE:
1. Maintain the EXACT original camera viewpoint, perspective, street angle, horizon, and spatial layout of the buildings and terrain.
2. DO NOT generate an unrelated scene, generic city, or different location. Edit the actual features of this specific image.
3. Realistic physical improvements to apply:
   - Damaged / dirt road -> clean, properly constructed and paved asphalt/concrete road with painted road markings.
   - Open / clogged drains -> modern, safe covered underground drainage with access manholes and clean curbs.
   - Accumulated garbage / litter -> completely clean surroundings with modern enclosed waste collection bins.
   - Dilapidated housing -> upgraded durable plastered and painted exterior walls, weather-proof roofs, and proper doors/windows.
   - Missing lighting -> installed energy-efficient warm LED streetlights along the street.
   - Poor paths -> paved pedestrian sidewalk / footpath with tactile paving.
   - Underdeveloped open ground -> modest urban greenery, tidy tree plantings, and community flower beds.
Current site problems: {problems_summary}.
Approved physical improvements: {recs_summary}.
Additional design notes: {design_guidance}.
Realistic Indian municipal context, believable human scale, authentic materials.
NO futuristic luxury skyscrapers, NO flyovers, NO fantasy architecture, NO text, NO watermarks, NO logos."""

    model = _setting("OPENAI_IMAGE_MODEL", "gpt-image-1")

    # Call OpenAI Images Edit endpoint
    try:
        # Standard parameters for gpt-image-1 or compatible image edit models
        kwargs = {
            "model": model,
            "image": ("underdeveloped-area.jpg", raw, "image/jpeg"),
            "prompt": prompt,
            "size": "1536x1024",
        }
        # Attempt high quality & png output if supported
        try:
            response = client.images.edit(
                **kwargs,
                quality="high",
                output_format="png",
            )
        except Exception:
            # Fallback to standard parameters if model/SDK prefers defaults
            response = client.images.edit(
                **kwargs,
            )
    except Exception as exc:
        raise RuntimeError(f"Image editing failed using model '{model}': {exc}") from exc

    if not getattr(response, "data", None) or len(response.data) == 0:
        raise RuntimeError("The image API returned an empty image list. Please check your model access and try again.")

    first_item = response.data[0]
    # Check if b64_json or url is returned
    b64_data = getattr(first_item, "b64_json", None)
    if b64_data:
        try:
            return base64.b64decode(b64_data, validate=True)
        except Exception as exc:
            raise RuntimeError(f"Failed to decode base64 image data: {exc}") from exc

    image_url = getattr(first_item, "url", None)
    if image_url:
        try:
            import requests
            img_res = requests.get(image_url, timeout=60)
            if img_res.status_code == 200:
                return img_res.content
            raise RuntimeError(f"HTTP {img_res.status_code} when downloading generated image.")
        except Exception as exc:
            raise RuntimeError(f"Failed to download image from generated URL: {exc}") from exc

    raise RuntimeError("The image API response contained neither base64 data nor an image URL.")


def _friendly_error(exc):
    status = getattr(exc, "status_code", None)
    message = str(exc)
    lowered = message.lower()
    if status == 401 or "incorrect api key" in lowered or "invalid api key" in lowered:
        return "Your OpenAI API key was rejected (HTTP 401). Check that OPENAI_API_KEY is correct, active, and has not expired."
    if status == 429 or "quota" in lowered or "billing" in lowered or "insufficient_quota" in lowered:
        return "Your OpenAI API quota or rate limit was reached (HTTP 429). Check your OpenAI account billing, available credits, and usage limits."
    if status in (400, 403, 404):
        return f"The API rejected the request (HTTP {status}). Check that the selected model is enabled for your OpenAI project and that your account has image generation/editing permissions. Details: {message}"
    if "timed out" in lowered or "timeout" in lowered:
        return "The AI request timed out. Image generation and vision models can take 30-90 seconds. Please check your internet connection and try again."
    return message


def _export_excel_budget(dataframe, subtotal, contingency, total):
    """Generate an Excel .xlsx workbook in memory."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Budget Estimate", index=False)
        summary_df = pd.DataFrame([
            {"Summary Metric": "Work Subtotal (₹)", "Amount (₹)": subtotal},
            {"Summary Metric": f"Contingency Allowance ({contingency}%) (₹)", "Amount (₹)": subtotal * (contingency / 100)},
            {"Summary Metric": "Total Budget Estimate (₹)", "Amount (₹)": total},
            {"Summary Metric": "Disclaimer", "Amount (₹)": "Indicative planning estimate only. Requires field measurements and local schedule-of-rates verification."},
        ])
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
    return output.getvalue()


def _render_budget(analysis):
    st.markdown("#### 💰 Preliminary Development Budget (Indicative)")
    st.caption(
        "Automatically generated preliminary budget based on photo analysis and identified infrastructure gaps. "
        "You can adjust quantities and unit rates to recalculate the budget."
    )

    interventions = analysis.get("interventions", [])
    if not interventions:
        interventions = list(INTERVENTION_METADATA.keys())[:5]

    rows = []
    st.markdown("##### Adjust Quantities and Unit Rates")
    for item in interventions:
        meta = INTERVENTION_METADATA.get(item, {
            "category": "Civil Works",
            "rate": 10000,
            "unit": "unit",
            "default_qty": 1,
            "default_priority": "High",
            "reason": "Infrastructure repair and development.",
        })

        category = meta["category"]
        unit = meta["unit"]
        default_qty = meta["default_qty"]
        default_rate = meta["rate"]
        priority = meta["default_priority"]
        reason = meta["reason"]

        with st.expander(f"📌 {item} ({category}) — Priority: {priority}", expanded=False):
            col_q, col_r = st.columns(2)
            with col_q:
                qty = st.number_input(
                    f"Quantity ({unit})",
                    min_value=0.0,
                    value=float(default_qty),
                    step=1.0,
                    key=f"ai_qty_{item}",
                )
            with col_r:
                unit_rate = st.number_input(
                    f"Unit Rate (₹ per {unit})",
                    min_value=0.0,
                    value=float(default_rate),
                    step=100.0,
                    key=f"ai_rate_{item}",
                )
            st.caption(f"**Reason for expenditure:** {reason}")

        total_item_cost = qty * unit_rate
        rows.append({
            "Development Activity": item,
            "Infrastructure Category": category,
            "Estimated Quantity": qty,
            "Unit": unit,
            "Unit Cost (₹)": unit_rate,
            "Total Cost (₹)": total_item_cost,
            "Priority": priority,
            "Reason for Expenditure": reason,
        })

    if rows:
        dataframe = pd.DataFrame(rows)
        subtotal = float(dataframe["Total Cost (₹)"].sum())

        st.dataframe(
            dataframe[[
                "Development Activity", "Infrastructure Category", "Estimated Quantity",
                "Unit", "Unit Cost (₹)", "Total Cost (₹)", "Priority", "Reason for Expenditure"
            ]],
            width="stretch",
            hide_index=True,
            column_config={
                "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%d"),
                "Total Cost (₹)": st.column_config.NumberColumn(format="₹%d"),
            }
        )

        c1, c2, c3 = st.columns([1, 1, 1.2])
        contingency = c1.slider("Contingency & Supervision (%)", 0, 25, 10, key="ai_development_contingency")
        total = subtotal * (1 + contingency / 100)
        c2.metric("Base Works Cost", f"₹{subtotal:,.0f}")
        c3.metric(f"Total Budget (incl. {contingency}% contingency)", f"₹{total:,.0f}")

        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            csv_data = dataframe.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Budget (CSV)",
                csv_data,
                "vikas_drishti_preliminary_budget.csv",
                "text/csv",
                key="ai_budget_download_csv",
                icon=":material/download:",
                width="stretch",
            )
        with col_xlsx:
            try:
                excel_data = _export_excel_budget(dataframe, subtotal, contingency, total)
                st.download_button(
                    "📥 Download Budget (Excel .xlsx)",
                    excel_data,
                    "vikas_drishti_preliminary_budget.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="ai_budget_download_excel",
                    icon=":material/download:",
                    width="stretch",
                )
            except Exception as exc:
                st.warning(f"Excel export unavailable: {exc}")

    st.warning(
        "⚠️ **Indicative Estimate Disclaimer:** All quantities, unit rates, and totals are planning-level "
        "preliminary estimates for project scoping and initial budget sanction. Detailed engineering estimates "
        "must be prepared through local topographic surveys, physical measurements, and current state/municipal Schedule of Rates (SoR)."
    )


def render_ai_development_recommendations():
    st.markdown("### 📸 AI Infrastructure Recommendations & Future View")
    st.caption(
        "Upload a photograph of any underdeveloped area. Vikas Drishti uses AI Vision to detect visible "
        "deficiencies, produces structured physical infrastructure recommendations, estimates an editable preliminary "
        "budget, and edits the photograph into a realistic conceptual future development image."
    )

    # API Key Configuration section
    with st.expander("🔑 OpenAI API Configuration", expanded=not bool(_api_key())):
        st.markdown("""
        **Secure Configuration Options:**
        1. **Session Input:** Enter your API key in the field below (retained in current session only).
        2. **Streamlit Secrets:** Add `OPENAI_API_KEY = "sk-..."` in `.streamlit/secrets.toml`.
        3. **Environment Variable:** Set `OPENAI_API_KEY` in your environment.

        *Supported Models:* Vision uses `gpt-4.1-mini`; Image editing uses `gpt-image-1`.
        """)
        st.text_input(
            "OpenAI API Key",
            type="password",
            key="ai_openai_api_key",
            placeholder="sk-proj-...",
            help="API keys are never stored permanently or logged.",
        )

    if not _api_key():
        st.warning("⚠️ No OpenAI API key configured. Provide an API key above or in `.streamlit/secrets.toml` to perform live analysis and image generation.")

    col_up, col_area = st.columns([1.5, 1])
    with col_up:
        uploaded = st.file_uploader(
            "Upload an underdeveloped-area photograph (JPG, JPEG, PNG)",
            type=["png", "jpg", "jpeg"],
            key="ai_development_photo",
        )
    with col_area:
        area = st.text_input(
            "Area / Location Name (Optional)",
            placeholder="Example: Ward 14, Dharavi / Ballari",
            key="ai_development_area",
        )

    raw = None
    preview_img = None
    photo_id = None
    if uploaded is not None:
        try:
            preview_img, raw = _image_bytes(uploaded)
            photo_id = hashlib.sha256(raw).hexdigest()
        except Exception as exc:
            st.error(str(exc))
            return

    # Check if a new photograph has been uploaded; clear state if photo changed
    previous_photo_id = st.session_state.get("ai_development_photo_id")
    if photo_id and previous_photo_id and photo_id != previous_photo_id:
        for key in (
            "ai_development_analysis",
            "ai_development_generated_image",
            "ai_development_generated_name",
            "ai_development_source_bytes",
        ):
            st.session_state.pop(key, None)

    if photo_id:
        st.session_state["ai_development_photo_id"] = photo_id
        st.session_state["ai_development_source_bytes"] = raw

    # Analysis Action Button
    api_ready = bool(_api_key())
    if st.button(
        "🔍 Analyse Photograph & Identify Infrastructure Needs",
        type="primary",
        width="stretch",
        disabled=(raw is None),
        key="ai_analyse_photo_button",
    ):
        if not api_ready:
            st.error("Please provide a valid OpenAI API key to start photo analysis.")
        else:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=_api_key(), timeout=240.0, max_retries=2)
                with st.spinner("AI Vision is inspecting the photograph for roads, drainage, garbage, sanitation, and housing gaps…"):
                    analysis = _analyze_site(client, raw, area.strip())

                # Retain analysis in session state
                st.session_state["ai_development_analysis"] = analysis
                st.session_state.pop("ai_development_generated_image", None)
                st.session_state["ai_development_generated_name"] = area.strip() or "Uploaded location"
                st.success("Photograph analysis complete. Review the findings and recommendations below.")
            except Exception as exc:
                st.error("AI photo analysis failed: " + _friendly_error(exc))

    analysis = (
        st.session_state.get("ai_development_analysis")
        if photo_id and photo_id == st.session_state.get("ai_development_photo_id")
        else None
    )

    # Display Analysis Results, Budget, and Image Generation Workflow
    if analysis:
        st.markdown("---")
        st.markdown("### 🔍 AI Vision Analysis Results")

        # 1. Identified Infrastructure Problems
        problems = analysis.get("identified_problems", [])
        if problems:
            st.markdown("#### 🚨 Identified Visible Infrastructure Problems")
            p_cols = st.columns(min(len(problems), 3)) if len(problems) <= 3 else None
            for idx, prob in enumerate(problems):
                urgency = prob.get("urgency", "High")
                urgency_color = (
                    "#b91c1c" if urgency == "Critical"
                    else "#ea580c" if urgency == "High"
                    else "#ca8a04" if urgency == "Medium"
                    else "#15803d"
                )
                with st.container():
                    st.markdown(
                        f"""
                        <div style="background:var(--surface);border-left:4px solid {urgency_color};padding:12px 16px;border-radius:6px;margin-bottom:10px;border:1px solid var(--line);">
                          <div style="display:flex;justify-content:space-between;align-items:center;">
                            <strong style="color:var(--ink);font-size:15px;">{prob.get('category')}: {prob.get('problem')}</strong>
                            <span style="background:{urgency_color};color:#fff;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600;">{urgency} Urgency</span>
                          </div>
                          <div style="color:var(--ink-2);margin-top:6px;font-size:14px;line-height:1.5;">{prob.get('explanation')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # 2. Practical Physical Improvement Recommendations
        recs = analysis.get("recommendations", [])
        if recs:
            st.markdown("#### 🛠️ Practical Physical Infrastructure Recommendations")
            for rec in recs:
                prio = rec.get("priority", "High")
                badge_bg = (
                    "#b91c1c" if prio == "Critical"
                    else "#ea580c" if prio == "High"
                    else "#ca8a04" if prio == "Medium"
                    else "#15803d"
                )
                with st.container():
                    st.markdown(
                        f"""
                        <div style="background:var(--surface);padding:12px 16px;border-radius:6px;margin-bottom:8px;border:1px solid var(--line);">
                          <div style="display:flex;justify-content:space-between;align-items:center;">
                            <strong style="color:var(--ink);font-size:14px;">{rec.get('category')} — {rec.get('action')}</strong>
                            <span style="background:{badge_bg};color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">{prio} Priority</span>
                          </div>
                          <div style="color:var(--muted);margin-top:4px;font-size:13px;">Expected Impact: {rec.get('impact')}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # 3. Preliminary Budget Estimation
        _render_budget(analysis)

        # 4. Realistic Future-Development Image Generation (Side-by-Side)
        st.markdown("---")
        st.markdown("### 🏙️ Future-Development Visualisation")
        st.caption(
            "Generate a realistic, conceptual future development image of THE SAME AREA based on the original photograph. "
            "AI edits the existing photograph while preserving viewpoint, layout, and building geometry."
        )

        generated = st.session_state.get("ai_development_generated_image")

        if generated:
            st.markdown("#### 🔄 Before & After: Side-by-Side Comparison")
            col_before, col_after = st.columns(2)
            with col_before:
                st.markdown("**Original Photograph (Current Condition)**")
                if preview_img:
                    st.image(preview_img, width="stretch", caption="Original Site View")
                elif st.session_state.get("ai_development_source_bytes"):
                    st.image(st.session_state["ai_development_source_bytes"], width="stretch", caption="Original Site View")
            with col_after:
                st.markdown("**Conceptual Future Development (AI Generated)**")
                st.image(
                    generated,
                    caption=f"Realistic Conceptual Future — {st.session_state.get('ai_development_generated_name', 'Selected location')}",
                    width="stretch",
                )

            col_down, col_retry = st.columns([1, 1])
            with col_down:
                st.download_button(
                    "📥 Download Improved Image (PNG)",
                    generated,
                    "vikas_drishti_future_development.png",
                    "image/png",
                    key="ai_future_image_download_btn",
                    icon=":material/download:",
                    width="stretch",
                )
            with col_retry:
                if st.button("🔄 Regenerate / Retry Image", key="ai_retry_future_image_button", width="stretch"):
                    try:
                        from openai import OpenAI
                        client = OpenAI(api_key=_api_key(), timeout=360.0, max_retries=2)
                        with st.spinner("AI is editing the photograph into an improved future development view…"):
                            new_gen = _generate_future_image(
                                client, st.session_state["ai_development_source_bytes"], area.strip(), analysis
                            )
                        st.session_state["ai_development_generated_image"] = new_gen
                        st.success("Future-development image regenerated successfully.")
                        st.rerun()
                    except Exception as exc:
                        st.error("AI future-image generation failed: " + _friendly_error(exc))
        else:
            # Display current photo preview
            if preview_img:
                st.image(preview_img, caption="Original Photograph — Ready for transformation", width="stretch")

            st.info("Your AI infrastructure analysis and budget are complete. Click below to generate the realistic conceptual future view.")
            if st.button(
                "✨ Generate Future Development Image",
                type="primary",
                width="stretch",
                disabled=not api_ready,
                key="ai_generate_future_image_btn",
            ):
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=_api_key(), timeout=360.0, max_retries=2)
                    with st.spinner("AI is editing your photograph into a realistic future development view. This may take 30-60 seconds…"):
                        generated_bytes = _generate_future_image(
                            client, st.session_state["ai_development_source_bytes"], area.strip(), analysis
                        )
                    st.session_state["ai_development_generated_image"] = generated_bytes
                    st.session_state["ai_development_generated_name"] = area.strip() or "Uploaded location"
                    st.success("Future-development image generated successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error("AI future-image generation failed: " + _friendly_error(exc))
                    st.caption(
                        "Note: Photo analysis and budget remain intact above. Check your API key, "
                        "project permissions for image editing, and network connection, then click retry."
                    )

        st.info(
            "ℹ️ **Planning Notice:** This is an AI-generated conceptual visualization for urban planning and participatory discussion. "
            "It does not represent an approved civil engineering design, statutory permit, or construction contract."
        )
    elif uploaded is not None and not analysis:
        # Show uploaded image preview before clicking analyse
        st.image(preview_img, caption="Uploaded Photograph (Current Condition)", width="stretch")
