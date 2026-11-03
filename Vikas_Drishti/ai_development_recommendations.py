"""AI photo assessment, same-photo future visualisation and indicative budget.

Configure OPENAI_API_KEY in .streamlit/secrets.toml or the environment.
Vision uses gpt-4.1-mini by default; image editing uses gpt-image-1 by default.
"""
import base64
import hashlib
import io
import json
import os

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

INTERVENTION_RATES = {
    "Road resurfacing": (1200, "sq. metre", 1000),
    "Covered drainage": (8500, "running metre", 250),
    "Street lights": (28000, "unit", 25),
    "Waste collection points": (45000, "unit", 8),
    "Pedestrian pathway": (2200, "sq. metre", 500),
    "Community water points": (180000, "unit", 3),
    "Parks and public spaces": (900, "sq. metre", 300),
    "Toilet / sanitation block": (1800000, "unit", 1),
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
    """Normalise uploaded PNG/JPEG to a clean, EXIF-correct JPEG for both APIs."""
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


def _analyze_site(client, raw, area):
    """Ask vision model for evidence-based visible observations and practical works."""
    data_url = "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    location_text = f" in {area}" if area else ""
    prompt = f"""Assess this photograph of an underdeveloped neighbourhood{location_text} in India.
Only describe conditions that are actually visible. Do not infer underground utilities,
ownership, exact dimensions, population or hidden risks. Recommend practical physical
infrastructure improvements. Return ONLY valid JSON using exactly this structure:
{{"observations":["visible condition"],"improvements":["specific physical improvement"],
"interventions":["one or more exact intervention names"],"design_prompt":"specific visual editing instructions"}}
The only allowed intervention names are: {', '.join(INTERVENTION_RATES.keys())}.
Give 3-6 observations and 4-8 improvements where the photo supports them. Prioritise safe
roads, covered drainage, sanitation, waste collection, clean water access, lighting,
pedestrian accessibility, greenery and climate resilience as relevant. Do not include prices.
Do not claim works are approved, funded or technically validated."""
    response = client.chat.completions.create(
        model=_setting("OPENAI_VISION_MODEL", "gpt-4.1-mini"),
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
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("The vision model returned an unreadable assessment. Please try again.") from exc

    for key in ("observations", "improvements", "interventions"):
        if not isinstance(result.get(key), list):
            result[key] = []
        result[key] = [str(item).strip() for item in result[key] if str(item).strip()]
    # Keep only supported costed work items, with a safe fallback if the model omits them.
    result["interventions"] = [
        item for item in result["interventions"] if item in INTERVENTION_RATES
    ]
    if not result["interventions"]:
        result["interventions"] = [
            "Road resurfacing", "Covered drainage", "Street lights", "Waste collection points"
        ]
    result["design_prompt"] = str(result.get("design_prompt", "")).strip()
    return result


def _generate_future_image(client, raw, area, analysis):
    """Edit the user's original photograph; do not generate an unrelated location."""
    observations = "; ".join(analysis.get("observations", [])) or "visible infrastructure gaps"
    improvements = "; ".join(analysis.get("improvements", [])) or "; ".join(analysis.get("interventions", []))
    location_text = f"Location context: {area}. " if area else ""
    prompt = f"""{location_text}Edit the supplied real photograph itself into a photorealistic
concept image showing how this exact underdeveloped Indian neighbourhood could look after
practical public infrastructure improvements. This is an IMAGE EDIT, not a new unrelated scene.
AI-visible existing conditions: {observations}.
Show these physical improvements clearly in the edited image: {improvements}.
{analysis.get('design_prompt', '')}
Preserve the original camera viewpoint, street direction, terrain, site layout and recognisable
building positions wherever possible. Keep realistic Indian neighbourhood scale, local materials,
construction logic and believable proportions. Improve only relevant visible infrastructure:
roads and footpaths, safe covered drains, street lighting, organised waste points, public water
access, sanitation facilities and modest greenery where appropriate. Do not add luxury towers,
unrealistic flyovers, impossible structures, text, labels, captions, logos or watermarks. Do not
turn the site into a different city. Output only the edited photorealistic image. The result is a
concept proposal, not an engineering drawing."""
    model = _setting("OPENAI_IMAGE_MODEL", "gpt-image-1")
    try:
        response = client.images.edit(
            model=model,
            image=("underdeveloped-area.jpg", raw, "image/jpeg"),
            prompt=prompt,
            size="1536x1024",
            quality="high",
            output_format="png",
        )
    except Exception as exc:
        # Surface the API's real error with model context; never silently substitute text output.
        raise RuntimeError(f"Image editing failed using model '{model}': {exc}") from exc
    if not getattr(response, "data", None) or not getattr(response.data[0], "b64_json", None):
        raise RuntimeError("The image API returned no image data. Check model access and try again.")
    try:
        return base64.b64decode(response.data[0].b64_json, validate=True)
    except Exception as exc:
        raise RuntimeError("The image API response could not be decoded. Please try again.") from exc


def _friendly_error(exc):
    status = getattr(exc, "status_code", None)
    message = str(exc)
    lowered = message.lower()
    if status == 401 or "incorrect api key" in lowered or "invalid api key" in lowered:
        return "Your OpenAI API key was rejected. Check that OPENAI_API_KEY is correct, active and has not expired."
    if status == 429 or "quota" in lowered or "billing" in lowered:
        return "Your OpenAI API quota or rate limit was reached. Check API billing, credits and usage limits."
    if status in (400, 403, 404):
        return f"The API rejected the request (HTTP {status}). Check that the selected model is available to your API project and that image-generation access is enabled. Details: {message}"
    if "timed out" in lowered or "timeout" in lowered:
        return "The AI request timed out. Check your internet connection and retry; image editing can take a few minutes."
    return message


def _render_budget(analysis):
    st.markdown("#### Preliminary development budget (indicative)")
    rows = []
    for item in analysis.get("interventions", []):
        rate, unit, default_qty = INTERVENTION_RATES[item]
        col1, col2 = st.columns(2)
        with col1:
            qty = st.number_input(
                f"{item} — {unit}", min_value=0.0, value=float(default_qty), step=1.0,
                key=f"ai_qty_{item}",
            )
        with col2:
            unit_rate = st.number_input(
                f"Rate per {unit} (₹)", min_value=0.0, value=float(rate), step=100.0,
                key=f"ai_rate_{item}",
            )
        rows.append({
            "Development work": item, "Quantity": qty, "Unit": unit,
            "Rate (₹)": unit_rate, "Estimated amount (₹)": qty * unit_rate,
        })
    if rows:
        dataframe = pd.DataFrame(rows)
        subtotal = float(dataframe["Estimated amount (₹)"].sum())
        contingency = st.slider("Contingency allowance (%)", 0, 25, 10, key="ai_development_contingency")
        total = subtotal * (1 + contingency / 100)
        st.dataframe(dataframe, width="stretch", hide_index=True)
        first, second = st.columns(2)
        first.metric("Work estimate", f"₹{subtotal:,.0f}")
        second.metric("Total incl. contingency", f"₹{total:,.0f}")
        st.download_button(
            "Download preliminary budget (CSV)", dataframe.to_csv(index=False).encode("utf-8"),
            "vikas_drishti_preliminary_budget.csv", "text/csv", key="ai_budget_download",
        )


def render_ai_development_recommendations():
    st.markdown("### AI future development visualizer")
    st.caption(
        "Upload a photograph of any underdeveloped area. AI analyses visible conditions, "
        "recommends physical infrastructure improvements, estimates a preliminary budget, "
        "and edits the same photograph to show a realistic possible future development."
    )
    if not _setting("OPENAI_API_KEY") and not st.session_state.get("ai_openai_api_key"):
        st.info("To enable live AI analysis and image generation, paste your OpenAI API key below. The key is kept in this browser session only and is not saved in the project ZIP.")
    entered_key = st.text_input(
        "OpenAI API key", type="password", key="ai_openai_api_key",
        placeholder="sk-... (or configure OPENAI_API_KEY in .streamlit/secrets.toml)",
        help="Required for real AI photo analysis and future-image editing. API usage may incur charges.",
    )
    if not _api_key():
        st.warning("No API key is configured yet. Enter your OpenAI API key above or add OPENAI_API_KEY to .streamlit/secrets.toml. The AI action will explain the issue if you try without a key.")

    uploaded = st.file_uploader(
        "Upload an underdeveloped-area photograph", type=["png", "jpg", "jpeg"],
        key="ai_development_photo",
    )
    area = st.text_input(
        "Area / location name (optional)", placeholder="Example: Ward 12, Ballari",
        key="ai_development_area",
    )

    raw = None
    photo_id = None
    if uploaded is not None:
        try:
            preview, raw = _image_bytes(uploaded)
            photo_id = hashlib.sha256(raw).hexdigest()
            st.image(preview, caption="Uploaded location — current condition", width="stretch")
        except Exception as exc:
            st.error(str(exc))
            return

    # Do not accidentally show a previous site's report/image after a new photo is selected.
    previous_photo_id = st.session_state.get("ai_development_photo_id")
    if photo_id and previous_photo_id and photo_id != previous_photo_id:
        for key in (
            "ai_development_analysis", "ai_development_generated_image",
            "ai_development_generated_name", "ai_development_source_bytes",
        ):
            st.session_state.pop(key, None)
    if photo_id:
        st.session_state["ai_development_photo_id"] = photo_id
        st.session_state["ai_development_source_bytes"] = raw

    api_ready = bool(_api_key())
    if st.button(
        "Analyse photograph and prepare recommendations", type="primary", width="stretch",
        disabled=(raw is None), key="ai_analyse_photo_button",
    ):
        if not api_ready:
            st.error("Add a valid OpenAI API key above before starting photo analysis.")
        else:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=_api_key(), timeout=240.0, max_retries=2)
                with st.spinner("AI is analysing the uploaded photograph and identifying visible infrastructure needs…"):
                    analysis = _analyze_site(client, raw, area.strip())
                # Save analysis before image generation so recommendations and budget remain available
                # even if the separate image endpoint is unavailable or needs a billing/model fix.
                st.session_state["ai_development_analysis"] = analysis
                st.session_state.pop("ai_development_generated_image", None)
                st.session_state["ai_development_generated_name"] = area.strip() or "Uploaded location"
                st.success("Photo analysis completed. Review the recommendations and preliminary budget below.")
            except Exception as exc:
                st.error("AI photo analysis failed: " + _friendly_error(exc))

    analysis = st.session_state.get("ai_development_analysis") if photo_id == st.session_state.get("ai_development_photo_id") else None
    if analysis:
        st.markdown("#### What AI identified in the uploaded area")
        observations = analysis.get("observations", [])
        if observations:
            st.markdown("**Visible conditions**")
            for item in observations:
                st.write("• " + str(item))
        improvements = analysis.get("improvements", [])
        if improvements:
            st.markdown("**Recommended physical infrastructure improvements**")
            for item in improvements:
                st.write("• " + str(item))
        _render_budget(analysis)

        st.markdown("#### AI-generated future development view")
        generated = st.session_state.get("ai_development_generated_image")
        if generated:
            st.image(
                generated,
                caption=f"Conceptual future view — {st.session_state.get('ai_development_generated_name', 'Selected location')}",
                width="stretch",
            )
            st.download_button(
                "Download generated future image", generated,
                "vikas_drishti_future_development.png", "image/png",
                key="ai_future_image_download",
            )
        else:
            st.info("Your AI recommendations and budget are ready. Generate the future-view image below; you can retry this separately if image generation fails.")
            if st.button(
                "Generate / retry future development image", type="primary", width="stretch",
                disabled=not api_ready, key="ai_generate_future_image_button",
            ):
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=_api_key(), timeout=360.0, max_retries=2)
                    with st.spinner("AI is editing your original photograph into a realistic future-development view. This may take a few minutes…"):
                        generated = _generate_future_image(
                            client, st.session_state["ai_development_source_bytes"], area.strip(), analysis
                        )
                    st.session_state["ai_development_generated_image"] = generated
                    st.session_state["ai_development_generated_name"] = area.strip() or "Uploaded location"
                    st.success("Future-development image generated successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error("AI future-image generation failed: " + _friendly_error(exc))
                    st.caption(
                        "The photo analysis and budget remain saved above. Check the image model "
                        "setting, API project access, billing and internet connection, then retry."
                    )

        st.info(
            "This is an AI-generated concept for planning and discussion, not a survey, "
            "engineering design, government approval or construction guarantee."
        )

    st.caption(
        "Budget figures are indicative planning allowances only. Validate site measurements, "
        "local schedule-of-rates, utility conditions, design and approvals with qualified "
        "local professionals before decisions."
    )
