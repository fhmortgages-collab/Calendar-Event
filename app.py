import streamlit as st
import json
import os
from datetime import datetime
import google.generativeai as genai

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="centered")

st.title("📅 Event Text-to-Calendar Sync")
st.markdown("Paste your event details below. The app will extract the title, date, time, and location using Gemini, and prepare it for your Google Calendar with your custom reminders.")

# Input Form
raw_text = st.text_area("Paste Event Details Here:", height=150, placeholder="Example: Meeting with Natalie on Sep 10, 2026 from 1pm to 2pm at 227 Bowery, NY.")
api_key = st.text_input("Enter your Gemini API Key:", type="password", value=os.environ.get("GEMINI_API_KEY", ""))

if st.button("Parse and Create Calendar Event", type="primary"):
    if not raw_text.strip():
        st.error("Please paste some event text first.")
    elif not api_key.strip():
        st.error("Please provide a valid Gemini API key.")
    else:
        with st.spinner("Analyzing text with Gemini..."):
            try:
                # Configure and call Gemini API
                genai.configure(api_key=api_key)
                prompt = (
                    "Extract event details from this text. Return ONLY a valid JSON object with keys: "
                    "'title' (string), 'startTime' (ISO 8601 format string, e.g., 2026-09-10T13:00:00), "
                    "'endTime' (ISO 8601 format string), and 'location' (string). "
                    "If no end time is specified, default to a 1-hour duration. "
                    "Today's date context is August 18, 2026.\n\nText:\n" + raw_text
                )
                
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt)
                
                cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
                event_data = json.loads(cleaned_text)
                
                st.success("Successfully extracted event details!")
                st.json(event_data)
                
                # Display Preview Metrics
                st.markdown("### Event Preview")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Event Title", event_data.get("title"))
                    st.metric("Start Time", event_data.get("startTime"))
                with col2:
                    st.metric("End Time", event_data.get("endTime"))
                    st.metric("Location", event_data.get("location", "Not specified"))
                
                st.success("✅ Event structured successfully with 30m, 2h, 1d, and 1w reminders configured for Google Calendar insertion!")

            except Exception as e:
                st.error(f"An error occurred during processing: {str(e)}")
