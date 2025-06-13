import streamlit as st
import requests
import json
import os
from datetime import datetime

# Configuration
ALFRED_API_URL = os.getenv("ALFRED_API_URL", "http://agent-core:8011")
ALFRED_MODEL_ROUTER_URL = os.getenv("ALFRED_MODEL_ROUTER_URL", "http://model-router:8080")
ENABLE_DIRECT_INFERENCE = os.getenv("ENABLE_DIRECT_INFERENCE", "true").lower() == "true"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "model" not in st.session_state:
    st.session_state.model = "llama3:8b"

# Page config
st.set_page_config(
    page_title="Alfred Chat",
    page_icon="🤖",
    layout="wide"
)

# Title and header
st.title("🤖 Alfred Chat UI")
st.caption(f"Connected to: {ALFRED_API_URL}")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Model selection
    st.session_state.model = st.selectbox(
        "Model",
        ["llama3:8b", "gpt-3.5-turbo", "gpt-4"],
        index=0
    )
    
    # Connection status
    try:
        response = requests.get(f"{ALFRED_API_URL}/health", timeout=2)
        if response.status_code == 200:
            st.success("✅ Connected to Agent Core")
        else:
            st.error("❌ Agent Core not responding")
    except:
        st.error("❌ Cannot connect to Agent Core")
    
    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Prepare the request payload
            payload = {
                "model": st.session_state.model,
                "messages": [{"role": msg["role"], "content": msg["content"]} 
                           for msg in st.session_state.messages]
            }
            
            # Make request to agent-core
            with st.spinner("Thinking..."):
                response = requests.post(
                    f"{ALFRED_API_URL}/api/v1/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    full_response = result.get("response", "No response received")
                else:
                    full_response = f"Error: {response.status_code} - {response.text}"
                    
        except requests.exceptions.Timeout:
            full_response = "Request timed out. Please try again."
        except requests.exceptions.ConnectionError:
            full_response = "Cannot connect to Alfred Agent Core. Please check if the service is running."
        except Exception as e:
            full_response = f"An error occurred: {str(e)}"
        
        message_placeholder.markdown(full_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Footer
st.divider()
st.caption(f"Alfred Agent Platform v2 | Model: {st.session_state.model}")