# Automated Shipping Document Verification Pipeline

An AI-powered pipeline built with Grok and Streamlit to automate inbox processing, email classification, shipping instruction (SI) & bill of lading (BL) document extraction, and discrepancy detection.

---

## Features

- **Email Classification:** Automatically categorizes inbound logistics emails (`BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, `SPAM`).
- **Structured Multimodal Extraction:** Uses Google Gemini with Pydantic schema enforcement to extract key shipment details (shipper, consignee, notify party, ports, container counts, weights).
- **Automated Discrepancy Auditing:** Compares SI and BL documents to flag discrepancies down to field-level mismatches.
- **Interactive Dashboard:** Built using Streamlit to monitor processing, review flagged items, inspect JSON details, and trigger evaluation server submissions.

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10+
- A Grok API Key

### 2. Install Dependencies

Open your terminal in the project root directory (`shipping-verification-project`) and run:

```bash
pip install streamlit google-genai pydantic python-dotenv requests
```

---

## Configuration

### Environment Variables (.env)
Create a `.env` file in the root folder (`shipping-verification-project/.env`):

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### Streamlit Secrets (.streamlit/secrets.toml)
For Streamlit integration, create `.streamlit/secrets.toml` in the project root:

```toml
GEMINI_API_KEY = "your_actual_gemini_api_key_here"
```

---

## Project Structure

```text
shipping-verification-project/
├── .streamlit/
│   └── secrets.toml          # Streamlit configuration file
├── data/
│   ├── inbox/                # Email JSON files
│   └── attachments/          # PDF/image attachments (BLs and SIs)
├── .env                      # Local environment variable file
├── app.py                    # Streamlit Dashboard UI
├── solution.py               # Core processing pipeline & Gemini integration
├── sample_submission.json    # Pipeline output file
└── README.md
```

---

## How to Run

### Option 1: Streamlit Dashboard (Recommended UI)

Run the dashboard directly:

```bash
streamlit run app.py
```

- Navigate to `http://localhost:8501`.
- Click **"Run Full Pipeline (Background)"** in the left sidebar to start processing emails.
- Search and expand individual audit records to see discrepancies.
- Optionally click **"Submit to Local Docker Scoreboard"** to test against the evaluation endpoint.

### Option 2: Command Line Backend Script

To process the inbox directly via Python:

```bash
python solution.py
```

*Note: By default, line 143 in `solution.py` limits execution to 3 emails for fast testing (`email_files = email_files[:3]`). Remove or adjust this slice to run the full dataset.*
