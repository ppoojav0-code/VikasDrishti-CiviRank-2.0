# Vikas Drishti – Smart Slum Development Monitoring & Decision Support

This update keeps the existing project modules and adds a role-based login screen, sidebar navigation, improved light/dark theme visibility, and a dedicated Smart Priority Scoring page.

## Included features
- **Role-based login:** Administrator, Government Officer, NGO, Viewer, and Data Analyst demo accounts. The front page includes both Sign in and Create account.
- **Dashboard:** Area ranking and overview metrics.
- **Smart Priority Scoring:** Explainable 0–100 score and Critical / High / Medium / Low classification.
- **Advanced Analytics:** Priority charts and risk distribution.
- **ML Clustering:** K-means grouping of areas using available service indicators.
- **GIS Map:** Location map when the uploaded CSV includes `Latitude` and `Longitude`.
- **AI Recommendations:** Rule-based recommendations tied to infrastructure gaps. This is an explainable rules-based prototype, not a trained generative AI model.
- **Early Warning System:** Threshold-based assessment of rainfall, drainage, flood history and heat index. It is not connected to a live weather or government alert feed.
- CSV upload and processed report download.

## Demo logins

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `Admin@123` |
| Administrator | `administrator` | `Admin@123` |
| Viewer | `viewer` | `Viewer@123` |
| NGO | `ngo` | `Ngo@123` |
| Data Analyst | `dataanalyst` | `Analyst@123` |

These local demo accounts are created automatically the first time the login page opens. Existing accounts are never overwritten. These credentials are for classroom/demo use only; remove or change them before public deployment. New self-registered accounts are activated immediately without email verification.

## CSV format

`Area` is required in practice; `Population` and service indicators are supported. Service indicator values should be numeric from 0 (very poor) to 100 (good); the app converts these fixed-scale values to 0–1 (it does not rescale each uploaded dataset relative to its own minimum and maximum). `Crime` is interpreted as severity, so higher values mean greater concern. Optional coordinates: `Latitude`, `Longitude`.

The priority score is calculated from the available indicators in the uploaded dataset. It is a decision-support ranking and should be checked against field observations before funding or emergency decisions.

## Run on Windows

1. Extract the ZIP file.
2. Open the extracted `Vikas_Drishti` folder in VS Code.
3. Open the VS Code terminal in that folder.
4. Create a fresh Python environment and install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Start the app:

   ```powershell
   python -m streamlit run app.py
   ```

You can also double-click `run_app.bat` after installing the dependencies. Use a fresh environment on your computer rather than copying a virtual environment from another machine, because virtual environments contain machine-specific paths.

## AI development image generation

The AI Recommendations page now includes an image-to-image conceptual development workflow and an editable preliminary budget estimate. The budget calculator works without an API key. To generate an improved concept image, install dependencies and configure an OpenAI API key. The old `gpt-image-1` model has been retired; this project now defaults to `gpt-image-1`:

```bash
pip install -r requirements.txt
```

On the AI Recommendations page, you can paste your API key into the password-style **OpenAI API key** field; it is held only in the current browser session. Alternatively, set `OPENAI_API_KEY` as an environment variable, or add this to `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "your-openai-api-key"
OPENAI_VISION_MODEL = "gpt-4.1-mini"
OPENAI_IMAGE_MODEL = "gpt-image-1"
```

Open **AI Recommendations**, upload a JPG or PNG photograph of any underdeveloped area, and select **Analyse photograph and prepare recommendations**. AI identifies visible conditions and practical physical improvements, then provides an editable preliminary budget. Select **Generate / retry future development image** to edit the same uploaded photograph into a realistic conceptual future view. Download the generated PNG. The image and budget are conceptual planning aids and must be validated locally.

## New: Cluster-to-scheme and corporator action workflow

- **Interpretable K-means clusters:** the model groups areas using available service indicators. Higher service values indicate better access; Crime is treated as severity. Cluster labels are ordered from the most deprived profile to the relatively better-served profile. The page includes an interactive 3D scatter view, cluster population summaries and a service-score heatmap.
- **Government scheme matching:** the `Scheme & Corporator Action` page links identified gaps to potential pathways under PMAY-U 2.0 (housing), AMRUT 2.0 (water/sewerage), Swachh Bharat Mission–Urban 2.0 (sanitation/wastewater), and DAY-NULM/livelihood convergence when relevant livelihood fields are present. These are data-based leads, not eligibility decisions or guaranteed funding. Confirm current guidelines, State participation, land/tenure conditions, beneficiary eligibility and ULB approval.
- **Ward representative directory:** upload a verified CSV with columns `Area,Ward,Corporator_Name,Email,Phone,Municipal_Body`. A starter file is available at `data/corporator_directory_template.csv`. The application deliberately does not invent corporator names or contact details when no verified mapping is supplied.
- **Corporator notification:** the app creates an area-specific situation report, previews it and allows a text draft download. Actual email sending is enabled only when a verified email and SMTP settings are configured. Set `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM` as environment variables. Delivery attempts are logged in `data/corporator_notification_log.csv`.
- **Single common login:** all roles continue to use the same login page; existing role-based page permissions are retained, with the new action page exposed to relevant operational roles.

### Suggested additional dataset columns

Existing columns continue to work. For more targeted scheme matching, you can optionally add `Livelihood_Gap` and/or `Unemployment_Rate` (0–100, where higher means a larger gap). Use verified ward boundaries and public office contact information in the corporator directory. The sample area names/coordinates are demonstration data and do not identify current elected representatives.

### Official scheme references

- PMAY-U 2.0: https://pmay-urban.gov.in/ (scheme guidance and eligibility are subject to current official rules)
- AMRUT: https://amrut.gov.in/
- Swachh Bharat Mission–Urban: https://swachhbharaturban.gov.in/
- DAY-NULM: https://nulm.gov.in/


## UI refresh (login and application interface)

- **Login:** one common, responsive sign-in page for every role, with new branding, a show/hide password control, and clear validation messages. Authentication and role-based access are unchanged; each role lands on its own dashboard.
- **Interface:** a consistent navy and teal design system (`assets/style.css`) with a redesigned sidebar, KPI cards, tables, charts and light/dark modes. The page-title block and page order are unchanged.
- **Clustering and map:** fixed cluster colours with legends, cluster summary cards, a geographic cluster map (when `Latitude`/`Longitude` exist), an annotated service heatmap, and a GIS map with risk-level layers, switchable base maps, a legend and fullscreen.
- **AI Recommendations:** the "Suggested projects for slum development in India" section was removed. The image workflow, budget estimate and dataset-based recommendations are unchanged.
- **Fix:** the corporator notification text now follows the selected area (previously it kept the first area's text).
- **Requirements:** `streamlit>=1.50.0` and `plotly>=5.24.0` (needed for current Streamlit widths and `scatter_map`).
- **Brand assets:** `assets/vikas_drishti_logo.svg` and `.png` were added; the original `vikas_logo.png` is kept.

## Account and corporator lookup configuration

New self-registered accounts are activated immediately without OTP, email verification, SMTP or Twilio. All new accounts receive the Data Analyst & Viewer role. Older account databases are preserved; Administrator and Government Officer access remains restricted to authorised assignment.

**Corporator public-source search:** Configure `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_ID` from Google Programmable Search Engine to enable online public-source lookup in the Scheme & Corporator Action page. Search snippets are leads only. Verify representative names and official contact details against an official municipal/election source before saving them.

For deployment, store secrets in the hosting platform's secret manager. Do not commit real credentials. SQLite account data is stored locally in `data/vikas_drishti_accounts.db`; use persistent storage and HTTPS for a deployed multi-user service.

### Updated account roles and image generation

- `Data Analyst` and `Viewer` are now one combined role: `Data Analyst & Viewer`. Existing account rows with either old role are migrated automatically; both previous demo logins now receive the combined role. The combined role keeps the Data Analyst pages and adds the Viewer map access.
- Self-registration now activates accounts immediately without email/SMS verification. New accounts receive `Data Analyst & Viewer`; Administrator and Government Officer remain restricted to authorised assignment.
- AI photo editing uses the current OpenAI GPT Image edit endpoint and defaults to `gpt-image-1`. Set `OPENAI_API_KEY` and optionally `OPENAI_IMAGE_MODEL` in `.streamlit/secrets.toml`. Never paste a real API key into source code or commit it to Git. API use may incur charges.

Example `.streamlit/secrets.toml` (create this file locally; do not upload it publicly):

```toml
OPENAI_API_KEY = "your-real-openai-api-key"
OPENAI_IMAGE_MODEL = "gpt-image-1"
```


## Updated account creation and AI future-view workflow

- The public entry page retains both **Sign in** and **Create account** tabs. Newly created accounts are activated immediately, require no email verification or OTP, and are automatically signed in with the Data Analyst & Viewer role.
- The AI Recommendations page uses OpenAI vision to inspect an uploaded photograph, identify visible infrastructure gaps, recommend practical physical improvements, and build an indicative budget. A separate retryable image-edit step edits the same photograph into a realistic conceptual future-development image. Analysis and budget remain visible even if image generation fails, so users can correct API access and retry image generation without re-running the analysis.
- Configure your own API key in `.streamlit/secrets.toml` (copy `.streamlit/secrets.toml.example`):

  ```toml
  OPENAI_API_KEY = "your-real-api-key"
  OPENAI_VISION_MODEL = "gpt-4.1-mini"
  OPENAI_IMAGE_MODEL = "gpt-image-1"
  ```

  Install dependencies with `python -m pip install -r requirements.txt`. API calls require internet access and an API account with billing/usage available; image and vision calls may incur charges. The ZIP intentionally contains no secret API key.

