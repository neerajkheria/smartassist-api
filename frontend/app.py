import streamlit as st
import requests
import json
import time

st.set_page_config(
    page_title="SmartAssist AI Portal",
    page_icon="🛡️",
    layout="wide"
)

# ----------------- Sidebar Configuration -----------------
st.sidebar.title("⚙️ System Gateway")
api_base_url = st.sidebar.text_input(
    "FastAPI Base URL", 
    value="http://localhost:8000",
    help="Point to your local uvicorn host or live Azure App Service URL"
).rstrip("/")

# Health check probe
st.sidebar.subheader("Connection Status")
try:
    health_res = requests.get(f"{api_base_url}/healthz", timeout=3)
    if health_res.status_code == 200:
        data = health_res.json()
        st.sidebar.success(f"Online (Pod: {data.get('pod_ip', 'Local')})")
    else:
        st.sidebar.error(f"Degraded: HTTP {health_res.status_code}")
except Exception:
    st.sidebar.error("Service Unreachable")

st.sidebar.markdown("---")
st.sidebar.caption("SmartAssist AI • Cloud-Native Enterprise Support")

# ----------------- Main Interface -----------------
st.title("🛡️ SmartAssist AI Operations Portal")
st.markdown("Enterprise incident triage, automated classification, and model telemetry dashboard.")

tab1, tab2, tab3, tab4 = st.tabs([
    "💬 Live Incident Triage", 
    "🏷️ Ticket Classifier", 
    "📦 Batch Engine", 
    "📊 Token Governance"
])

# ----------------- Tab 1: Live Incident Triage -----------------
with tab1:
    st.subheader("Customer SLA Incident Diagnosis")
    col1, col2 = st.columns([1, 2])

    with col1:
        customer_selection = st.selectbox(
            "Customer SLA Profile",
            options=["CUST-101", "CUST-102", "GENERIC"],
            format_func=lambda x: {
                "CUST-101": "CUST-101 (Contoso: Mission-Critical / AKS)",
                "CUST-102": "CUST-102 (Fabrikam: Standard / S2S VPN)",
                "GENERIC": "Generic (No Profile Injection)"
            }[x]
        )
        max_tokens_input = st.slider("Max Completion Tokens", min_value=100, max_value=1000, value=400, step=50)

    with col2:
        user_query = st.text_area(
            "Incident Description / Query",
            placeholder="e.g., Pods in East US 2 cluster cannot reach internal database over VPN tunnel.",
            height=130
        )
        run_triage = st.button("Run Diagnostic Triage", type="primary")

    if run_triage:
        if not user_query.strip():
            st.warning("Please provide an incident description.")
        else:
            endpoint = "/api/v1/support/query" if customer_selection == "GENERIC" else "/api/v1/support/query/contextual"
            payload = {"query": user_query, "max_tokens": max_tokens_input}
            if customer_selection != "GENERIC":
                payload["customer_id"] = customer_selection

            with st.spinner("Analyzing against cloud knowledge base..."):
                try:
                    res = requests.post(f"{api_base_url}{endpoint}", json=payload, timeout=45)
                    if res.status_code == 200:
                        data = res.json()
                        st.success("Triage Response Generated")
                        st.markdown(data.get("response", "No content returned."))
                        
                        if "tokens" in data and data["tokens"]:
                            tok = data["tokens"]
                            st.caption(f"Prompt Tokens: {tok.get('prompt_tokens')} | Completion: {tok.get('completion_tokens')} | Total: {tok.get('total_tokens')}")
                    else:
                        st.error(f"Inference error ({res.status_code}): {res.text}")
                except Exception as e:
                    st.error(f"Failed to connect to backend: {str(e)}")

# ----------------- Tab 2: Ticket Classifier -----------------
with tab2:
    st.subheader("Few-Shot Ticket Classification")
    ticket_input = st.text_area(
        "Support Ticket Content",
        placeholder="e.g., High latency and 40% packet drops observed on ExpressRoute primary gateway.",
        height=100
    )
    classify_btn = st.button("Classify Ticket")

    if classify_btn:
        if not ticket_input.strip():
            st.warning("Please enter ticket text to evaluate.")
        else:
            with st.spinner("Extracting taxonomy and priority..."):
                try:
                    res = requests.post(
                        f"{api_base_url}/api/v1/tickets/classify",
                        json={"ticket_text": ticket_input},
                        timeout=30
                    )
                    if res.status_code == 200:
                        out = res.json()
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Category", out.get("category", "Unknown"))
                        
                        priority = out.get("priority", "N/A")
                        c2.metric("Priority", priority)
                        c3.metric("Confidence Score", f"{out.get('confidence_score', 0.0) * 100:.1f}%")

                        st.info(f"**Reasoning:** {out.get('reasoning', 'N/A')}")
                    else:
                        st.error(f"Classification failed: {res.text}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")

# ----------------- Tab 3: Batch Engine -----------------
with tab3:
    st.subheader("Asynchronous Batch Incident Ingestion")
    st.markdown("Enter multiple incident queries (one per line) to process via FastAPI background workers.")

    batch_input = st.text_area(
        "Incident Lines (Batch Queue)",
        value="Storage blob authentication failing in West Europe\nUser locked out of bastion host after 3 failed password attempts\nHow do we scale AKS replicas using horizontal pod autoscaler?",
        height=120
    )
    submit_batch_btn = st.button("Submit Batch Processing Job")

    if submit_batch_btn:
        lines = [line.strip() for line in batch_input.split("\n") if line.strip()]
        if not lines:
            st.warning("Provide at least one ticket line.")
        else:
            with st.spinner("Submitting batch job..."):
                try:
                    res = requests.post(f"{api_base_url}/api/v1/batch/process", json={"tickets": lines}, timeout=10)
                    if res.status_code == 200:
                        batch_info = res.json()
                        job_id = batch_info["job_id"]
                        st.success(f"Batch queued! Job ID: {job_id}")

                        # Polling loop
                        status_placeholder = st.empty()
                        progress_bar = st.progress(0)
                        
                        for step in range(1, 11):
                            time.sleep(2)
                            poll = requests.get(f"{api_base_url}/api/v1/batch/{job_id}").json()
                            status = poll.get("status")
                            status_placeholder.info(f"Job Status: **{status.upper()}** (Checking step {step}/10)...")
                            progress_bar.progress(step * 10)
                            
                            if status == "completed":
                                status_placeholder.success("Batch Processing Complete!")
                                st.dataframe(poll.get("results", []))
                                break
                    else:
                        st.error(f"Submission failed: {res.text}")
                except Exception as e:
                    st.error(f"Error submitting batch: {str(e)}")

# ----------------- Tab 4: Token Governance -----------------
with tab4:
    st.subheader("Azure OpenAI Token Consumption Telemetry")
    if st.button("Refresh Telemetry Data"):
        try:
            res = requests.get(f"{api_base_url}/api/v1/support/tokens/metrics", timeout=5)
            if res.status_code == 200:
                metrics = res.json()
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total API Calls", metrics.get("total_requests", 0))
                m2.metric("Prompt Tokens", metrics.get("total_prompt_tokens", 0))
                m3.metric("Completion Tokens", metrics.get("total_completion_tokens", 0))
                m4.metric("Avg Tokens / Call", metrics.get("average_tokens_per_request", 0))
                
                st.json(metrics)
            else:
                st.error("Failed to load telemetry.")
        except Exception as e:
            st.error(f"Connection error: {str(e)}")
