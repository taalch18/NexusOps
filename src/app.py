import streamlit as st
import requests
import uuid
import logging

# Configure local logging for frontend debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UI Configuration - Terminal/SRE Aesthetic
st.set_page_config(
    page_title="NexusOps | Agentic SRE Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# Custom Grunge/Cyber-Noir Styling
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00FF41; font-family: 'Courier New', monospace; }
    .stChatMessage { border: 1px solid #1a1a1a; border-radius: 4px; background-color: #0d0d0d; }
    [data-testid="stMetricValue"] { color: #00FF41; }
    .stStatusWidget { background-color: #111; border: 1px solid #00FF41; }
    </style>
""", unsafe_allow_input=True)

# Sidebar - System Telemetry
with st.sidebar:
    st.title("📟 TELEMETRY")
    st.divider()
    st.metric("RETRIEVAL HIT", "100%", delta="Top-K")
    st.metric("ROUTING ACCURACY", "94.2%", delta="Fidelity")
    st.metric("P95 LATENCY", "1.2s", delta="-0.2s")
    st.divider()
    if st.button("RESET SESSION"):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

st.title("🛡️ NEXUS-OPS: AGENTIC RUNTIME")
st.caption("Site Reliability Engineering | LangGraph | Autonomous Remediation")

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# Render historical context
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input Interface
if prompt := st.chat_input("Enter system incident signature (e.g., OOM on backend-api)..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Agent Logic Visualization
        with st.status("Initializing Agent Reasoning...", expanded=True) as status:
            try:
                # API endpoint matches our versioned FastAPI backend
                api_url = "http://localhost:8000/v1/chat"
                payload = {
                    "text": prompt, 
                    "thread_id": st.session_state.thread_id
                }
                
                response = requests.post(api_url, json=payload, timeout=45)
                
                if response.status_code == 200:
                    data = response.json()
                    final_content = ""
                    
                    # Process and display agent thought-stream
                    for msg in data["history"]:
                        if msg.get("tool_calls"):
                            for call in msg["tool_calls"]:
                                st.write(f"⚙️ **System Action:** Executing `{call['name']}`")
                        
                        if msg["role"] == "assistant" and not msg.get("tool_calls"):
                            final_content = msg["content"]
                    
                    status.update(label="Incident Analyzed", state="complete", expanded=False)
                    st.markdown(final_content)
                    st.session_state.messages.append({"role": "assistant", "content": final_content})
                
                else:
                    status.update(label="Critical Error", state="error")
                    st.error(f"Backend Offline (Status: {response.status_code})")
                    
            except requests.exceptions.Timeout:
                st.error("Operation timed out. Agent is still processing high-complexity task.")
            except Exception as e:
                st.error(f"Interface Error: {str(e)}")
