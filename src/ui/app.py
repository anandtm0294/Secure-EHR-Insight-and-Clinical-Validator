import requests
import streamlit as st


API_CHAT_URL = "http://localhost:8000/api/v1/chat"
API_PATIENTS_URL = "http://localhost:8000/api/v1/patients"

st.set_page_config(page_title="Zero-Trust Clinical EHR", layout="centered")
st.title("Enterprise EHR chat")
st.caption("Protected by Presidio Zero-Trust and NeMo Guardrails")


@st.cache_data(ttl=300)
def fetch_patient_list() -> tuple[list[str], str | None]:
    try:
        response = requests.get(API_PATIENTS_URL, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            return [], payload["error"]
        return payload.get("patients", []), None
    except (requests.RequestException, ValueError) as exc:
        return [], str(exc)


patient_list, patient_error = fetch_patient_list()

if patient_error:
    st.sidebar.error(f"Database connection failed: {patient_error}")
    patient_id = None
elif not patient_list:
    st.sidebar.warning("No embedded patients found.")
    patient_id = None
else:
    patient_id = st.sidebar.selectbox(
        "Select patient file (type to search)",
        patient_list,
    )
    st.sidebar.info(
        f"Database explicitly locked to patient: {patient_id}",
        icon=":material/lock:",
    )

st.session_state.setdefault("messages", [])
st.session_state.setdefault("active_patient_id", patient_id)

if st.session_state.active_patient_id != patient_id:
    st.session_state.messages = []
    st.session_state.active_patient_id = patient_id

if st.sidebar.button("Clear chat", icon=":material/delete_sweep:"):
    st.session_state.messages = []
    st.rerun()

for message in st.session_state.messages:
    st.chat_message(message["role"]).write(message["content"])

prompt = st.chat_input(
    f"Ask about patient {patient_id}'s history..." if patient_id else "Patient data unavailable",
    disabled=patient_id is None,
)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    payload = {
        "patient_id": patient_id,
        "messages": st.session_state.messages,
    }

    with st.spinner("Analyzing securely..."):
        try:
            response = requests.post(API_CHAT_URL, json=payload, timeout=120)
            response.raise_for_status()
            bot_reply = response.json().get("llm_response")
            if not bot_reply:
                raise ValueError("The API returned an empty response.")
            bot_reply += (
                "\n\n*AI-generated summary. Do not use for diagnostic purposes.*"
            )
        except (requests.RequestException, ValueError) as exc:
            bot_reply = f"API error: {exc}"

    st.session_state.messages.append(
        {"role": "assistant", "content": bot_reply}
    )
    st.chat_message("assistant").write(bot_reply)
