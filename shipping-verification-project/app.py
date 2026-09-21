import os
import json
import requests
import time
import random
import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF

# ---------------------------------------------------------
# Page Configuration & Corporate Dark Mode CSS
# ---------------------------------------------------------
st.set_page_config(page_title="Averis AI", page_icon="🚢", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0f172a; color: #f8fafc; }

    .hero-text {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(to right, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        padding-bottom: 0px;
        letter-spacing: -1px;
    }
    .sub-hero {
        font-size: 1.1rem;
        font-weight: 400;
        color: #94a3b8;
        margin-bottom: 2.5rem;
    }

    div[data-testid="metric-container"] {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #38bdf8;
    }
    div[data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 800; color: #f8fafc; }
    div[data-testid="stMetricLabel"] { color: #94a3b8; font-weight: 600; }

    [data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #1e293b; }
    .streamlit-expanderHeader { background-color: #1e293b !important; border-radius: 6px; color: #f8fafc !important; }
    
    hr { border-color: #1e293b; }
    
    .eta-box {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 5px;
        border-left: 3px solid #818cf8;
        font-size: 0.9rem;
        margin-top: 10px;
    }
    .legend-container {
        background-color: #1e293b;
        padding: 12px 18px;
        border-radius: 8px;
        border: 1px solid rgba(148, 163, 184, 0.1);
        margin-bottom: 20px;
        display: flex;
        gap: 20px;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State for Cancellation
if "cancel_scan" not in st.session_state:
    st.session_state.cancel_scan = False

# ---------------------------------------------------------
# Data Loading 
# ---------------------------------------------------------
output_file = "sample_submission.json"
results = {}

if os.path.exists(output_file):
    with open(output_file, "r") as f:
        try:
            results = json.load(f)
        except json.JSONDecodeError:
            pass

# ---------------------------------------------------------
# PDF Generation Logic
# ---------------------------------------------------------
def generate_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16, style='B')
    pdf.cell(200, 10, txt="Averis Nexus AI - Executive Summary", ln=1, align='C')
    
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 10, txt=f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}", ln=1, align='C')
    pdf.ln(10)
    
    total = len(data)
    mismatches = sum(1 for r in data.values() if r.get("mismatch_found"))
    reviews = sum(1 for r in data.values() if r.get("needs_human_review"))
    
    pdf.set_font("Arial", size=12, style='B')
    pdf.cell(200, 10, txt="System Metrics:", ln=1)
    pdf.set_font("Arial", size=11)
    pdf.cell(200, 8, txt=f"Total Emails Processed: {total}", ln=1)
    pdf.cell(200, 8, txt=f"Data Mismatches Detected: {mismatches}", ln=1)
    pdf.cell(200, 8, txt=f"Corrupt/Unreadable Documents: {reviews}", ln=1)
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12, style='B')
    pdf.cell(200, 10, txt="Flagged Items (Action Required):", ln=1)
    pdf.set_font("Arial", size=10)
    
    for email_id, record in data.items():
        if record.get("mismatch_found") or record.get("needs_human_review"):
            status = "Mismatch Detected" if record.get("mismatch_found") else "Missing/Corrupt Docs"
            pdf.cell(200, 7, txt=f"- {email_id}: {status}", ln=1)
            
    return pdf.output(dest="S").encode("latin-1")

# ---------------------------------------------------------
# Sidebar Controls with Cancel & Restart Logic
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2760/2760205.png", width=70) 
    st.markdown("<h3 style='color: #f8fafc; margin-top: -10px;'>Operations</h3>", unsafe_allow_html=True)
    
    scan_limit = st.selectbox("Batch Size (New Emails)", ["1", "5", "10", "50", "All"], index=1)
    
    col_btn1, col_btn2 = st.columns(2)
    start_clicked = col_btn1.button("📥 Start", type="primary", width="stretch")
    cancel_clicked = col_btn2.button("🛑 Abort", type="secondary", width="stretch")

    if cancel_clicked:
        st.session_state.cancel_scan = True
        st.warning("⚠️ Abort signal sent. Stopping after current task...")

    if start_clicked:
        st.session_state.cancel_scan = False
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        start_time = time.time()
        
        def update_ui(current, total, email_id, category):
            pct = current / total
            progress_bar.progress(pct)
            
            elapsed = time.time() - start_time
            if current > 0:
                time_per_item = elapsed / current
                eta_seconds = time_per_item * (total - current)
                eta_mins, eta_secs = divmod(int(eta_seconds), 60)
                eta_str = f"{eta_mins}m {eta_secs}s"
            else:
                eta_str = "Calculating..."
                
            status_text.markdown(f"""
            <div class="eta-box">
                <b>Processing:</b> {email_id} ({category})<br>
                <b>Progress:</b> {current} / {total} files<br>
                <b>Time Elapsed:</b> {int(elapsed)}s<br>
                <b>Estimated Time Remaining:</b> <span style='color: #38bdf8;'>{eta_str}</span>
            </div>
            """, unsafe_allow_html=True)
            
        def check_cancel():
            return st.session_state.get("cancel_scan", False)

        try:
            from solution import DocumentVerificationSystem
            system = DocumentVerificationSystem(data_dir="data")
            system.process_inbox(progress_callback=update_ui, stop_callback=check_cancel, limit=scan_limit)
            
            if st.session_state.cancel_scan:
                st.toast('Scan Aborted by User', icon='🛑')
            else:
                st.toast('Scan Complete', icon='✅')
                
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Pipeline Error: {e}")
                
    if st.button("🔄 Refresh Dashboard", width="stretch"):
        st.session_state.cancel_scan = False
        st.rerun()

    st.markdown("---")
    st.markdown("<h3 style='color: #f8fafc;'>Reporting</h3>", unsafe_allow_html=True)
    
    if results:
        pdf_bytes = generate_pdf(results)
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name="Averis_Executive_Report.pdf",
            mime="application/pdf",
            width="stretch"
        )
    else:
        st.info("Run a scan to generate reports.")

# ---------------------------------------------------------
# Main App Header
# ---------------------------------------------------------
st.markdown('<div class="hero-text">Averis Nexus AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-hero">Automated Maritime Document Intelligence 🚢</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📊 Analytics Overview", "🔎 Audit Trail", "🏆 Evaluation Server", "⚙️ Live Simulator"])

# ==========================================
# TAB 1: AI ANALYTICS
# ==========================================
with tab1:
    if not results:
        st.info("Inbox is currently pending analysis. Use the sidebar to scan a batch.")
    else:
        total_emails = len(results)
        doc_comparisons = sum(1 for r in results.values() if r.get("category") == "BL_COMPARISON")
        mismatches_found = sum(1 for r in results.values() if r.get("mismatch_found"))
        human_reviews = sum(1 for r in results.values() if r.get("needs_human_review"))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Emails Ingested", total_emails)
        col2.metric("Deep Comparisons", doc_comparisons)
        col3.metric("🚨 Mismatches", mismatches_found, delta="Action Required", delta_color="inverse")
        col4.metric("⚠️ Corrupt Docs", human_reviews, delta="Human Review", delta_color="inverse")

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("#### Routing Classification Volume")
            categories = [r.get("category", "UNKNOWN") for r in results.values()]
            if categories:
                cat_df = pd.DataFrame({"Category": categories}).value_counts().reset_index()
                cat_df.columns = ["Category", "Volume"]
                fig = px.pie(cat_df, values='Volume', names='Category', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f8fafc", family="Inter"))
                st.plotly_chart(fig, width="stretch")

        with c2:
            st.markdown("#### Discrepancy Frequency by Field")
            mismatched_fields = []
            for r in results.values():
                disc = r.get("discrepancies", {})
                if isinstance(disc, dict): 
                    mismatched_fields.extend(disc.keys())
            
            if mismatched_fields:
                field_df = pd.DataFrame({"Field": mismatched_fields}).value_counts().reset_index()
                field_df.columns = ["Field", "Frequency"]
                fig2 = px.bar(field_df, x='Field', y='Frequency', text_auto=True, color='Field', color_discrete_sequence=px.colors.qualitative.Vivid)
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False, font=dict(color="#f8fafc", family="Inter"))
                st.plotly_chart(fig2, width="stretch")
            else:
                st.success("All processed documents match perfectly.")

# ==========================================
# TAB 2: AUDIT TRAIL
# ==========================================
with tab2:
    if not results:
        st.info("No data available.")
    else:
        st.markdown("""
        <div class="legend-container">
            <span style="font-weight: 700; color: #f8fafc; margin-right: 10px;">Status Legend:</span>
            <span>🟢 <b>Normal / Validated</b> (Passed Checks)</span>
            <span style="margin-left: 15px;">🟡 <b>Human Review Required</b> (Missing/Corrupt Docs)</span>
            <span style="margin-left: 15px;">🔴 <b>Data Mismatch</b> (SI vs BL Conflict)</span>
        </div>
        """, unsafe_allow_html=True)

        fc1, fc2, fc3 = st.columns([2, 1, 1])
        search_query = fc1.text_input("🔍 Search File Ref")
        filter_category = fc2.selectbox("📂 Filter by Route", ["All", "BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"])
        filter_flagged = fc3.checkbox("🚨 Show Only Exceptions")

        st.markdown("---")
        count_shown = 0
        for email_id, record in results.items():
            category = record.get("category")
            mismatch = record.get("mismatch_found")
            review = record.get("needs_human_review")
            
            if search_query and search_query.lower() not in email_id.lower(): continue
            if filter_category != "All" and category != filter_category: continue
            if filter_flagged and not (mismatch or review): continue
                
            count_shown += 1
            status_icon = "🔴" if mismatch else ("🟡" if review else "🟢")
            
            with st.expander(f"{status_icon} **{email_id}** | Route: {category}"):
                if review: 
                    st.warning("⚠️ **Human Review Required:** Missing or unreadable SI/BL attachments.")
                if mismatch and isinstance(record.get("discrepancies"), dict):
                    st.error("🚨 **Data Discrepancy Detected (SI vs BL)**")
                    
                    diff_data = [{
                        "Data Field": str(field).replace("_", " ").title(), 
                        "Shipping Instructions (SI)": str(vals.get("SI", "N/A")), 
                        "Bill of Lading (BL)": str(vals.get("BL", "N/A"))
                    } for field, vals in record["discrepancies"].items()]
                    
                    st.dataframe(pd.DataFrame(diff_data), width="stretch", hide_index=True)
                elif category == "BL_COMPARISON" and not review: 
                    st.success("✅ Validated. No discrepancies.")
                elif category != "BL_COMPARISON": 
                    st.info(f"Successfully routed to: {category}")

        if count_shown == 0: st.info("No matching records found.")

# ==========================================
# TAB 3: DOCKER SCOREBOARD
# ==========================================
with tab3:
    st.write("Submit finalized dataset to the Docker evaluation server.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("📤 Submit to Evaluation Server", type="primary", width="stretch"):
        with st.spinner("Connecting to localhost:8080..."):
            try:
                response = requests.post("http://localhost:8080/submit", json=results)
                if response.status_code == 200:
                    st.balloons()
                    st.success("Evaluation Successful.")
                    score_data = response.json()
                    
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("🏆 FINAL SCORE", f"{score_data.get('final_score', 0) * 100:.2f}%")
                    sc2.metric("🧠 Stage 1: Classification", f"{score_data.get('stage1', {}).get('accuracy', 0) * 100:.2f}%")
                    sc3.metric("🎯 Stage 3: Extraction", f"{score_data.get('stage3', {}).get('exact_match_rate', 0) * 100:.2f}%")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("🔍 View Raw JSON Metrics"): 
                        st.json(score_data)
                else: 
                    st.error(f"Server Error {response.status_code}: {response.text}")
            except Exception as e: 
                st.error("Connection Failed. Ensure Docker is running.")

# ==========================================
# TAB 4: LIVE TESTER
# ==========================================
with tab4:
    st.write("Isolate and verify a single email through the LLM pipeline.")
    
    if st.button("🎰 Randomize Email Sample", width="stretch"):
        inbox_path = "data/inbox"
        if not os.path.exists(inbox_path):
            st.error(f"Directory missing: {inbox_path}")
        else:
            files = [f for f in os.listdir(inbox_path) if f.endswith(".json")]
            if files:
                random_file = random.choice(files)
                email_id = random_file.replace(".json", "")
                
                with open(os.path.join(inbox_path, random_file), 'r') as f:
                    raw_email = json.load(f)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"#### 📨 Input Data: `{email_id}`")
                    st.info(f"**Subject:** {raw_email.get('subject')}")
                    st.text_area("Body", raw_email.get('body'), height=300, disabled=True)
                    st.write("**Attachments:**", ", ".join(raw_email.get('attachments', [])) or "None")
                
                with col2:
                    st.markdown("#### 🤖 LLM Output")
                    with st.spinner("Processing..."):
                        from solution import DocumentVerificationSystem
                        system = DocumentVerificationSystem(data_dir="data")
                        
                        start_time = time.time()
                        ai_result = system.process_single_email(email_id)
                        end_time = time.time()
                        
                    st.success(f"Processed in **{end_time - start_time:.2f}s**")
                    st.json(ai_result)
            else:
                st.warning("Inbox empty.")