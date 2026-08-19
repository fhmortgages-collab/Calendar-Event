import streamlit as st
import re
from datetime import datetime
from urllib.parse import quote
from pypdf import PdfReader

# Page Configuration
st.set_page_config(page_title="Event Parser & Calendar Sync", page_icon="📅", layout="centered")

st.title("📅 Event Text & PDF Parser")
st.markdown("Choose your preferred method below to extract event details and generate your Google Calendar link.")

# Input Method Selection
input_method = st.radio("Select Input Method:", ["Upload PDF File", "Paste Text Manually"])

extracted_text = ""

if input_method == "Upload PDF File":
    uploaded_file = st.file_uploader("Upload Event PDF:", type=["pdf"])
    if uploaded_file is not None:
        try:
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"
            st.success("Successfully extracted text from uploaded PDF!")
        except Exception as e:
            st.error(f"Error reading PDF file: {str(e)}")

# Editable text area populated either by PDF upload or manual pasting
raw_text = st.text_area(
    "Event Details:", 
    height=150, 
    value=extracted_text if extracted_text else "Team Lunch Meeting\nWednesday, September 09, 2026\n10Am to 1pm at Lafayette",
    placeholder="Paste event text here or upload a PDF above..."
)

if st.button("Parse and Generate Calendar Link", type="primary"):
    if not raw_text.strip():
        st.error("Please provide event details via PDF upload or text pasting first.")
    else:
        with st.spinner("Extracting details..."):
            try:
                lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                
                # 1. Title is the first line
                title = lines[0] if lines else "Untitled Event"
                
                # 2. Extract Date (e.g., "September 09, 2026")
                date_str = ""
                date_match = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', raw_text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1).replace(",", "")

                # 3. Flexible Time Range Extraction (e.g. "10Am to 1pm")
                start_time_str, end_time_str = "", ""
                time_range_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', raw_text, re.IGNORECASE)
                if time_range_match:
                    start_time_str = time_range_match.group(1).upper()
                    end_time_str = time_range_match.group(2).upper()

                # 4. Improved Location Extraction (checks explicit label or captures text following "at")
                location = ""
                loc_label_match = re.search(r'(?:location:)\s*([^\n]+)', raw_text, re.IGNORECASE)
                if loc_label_match:
                    location = loc_label_match.group(1).strip()
                else:
                    loc_at_match = re.search(r'\bat\s+([^\n]+)', raw_text, re.IGNORECASE)
                    if loc_at_match:
                        location = loc_at_match.group(1).strip()

                st.success("Successfully extracted details!")
                
                # Display Preview Metrics
                st.markdown("### Event Preview")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Event Title", title)
                    st.metric("Time", f"{start_time_str} - {end_time_str}" if start_time_str else "Not specified")
                with col2:
                    st.metric("Date", date_str if date_str else "Not specified")
                    st.metric("Location", location if location else "None provided")
                
                # Build Google Calendar URL
                base_cal_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
                encoded_title = quote(title)
                encoded_location = quote(location) if location else ""
                
                # Format dates and times into local GCal format (YYYYMMDDTHHMMSS)
                dates_param = ""
                if date_str and start_time_str and end_time_str:
                    try:
                        parsed_date = datetime.strptime(date_str, "%B %d %Y")
                    except:
                        try:
                            parsed_date = datetime.strptime(date_str, "%b %d %Y")
                        except:
                            parsed_date = None
                            
                    if parsed_date:
                        date_formatted = parsed_date.strftime("%Y%m%d")
                        
                        def parse_time_flexible(t_str):
                            t_str = t_str.replace(" ", "")
                            for fmt in ("%I:%M%p", "%I%p"):
                                try:
                                    return datetime.strptime(t_str, fmt)
                                except ValueError:
                                    continue
                            return None

                        start_dt = parse_time_flexible(start_time_str)
                        end_dt = parse_time_flexible(end_time_str)
                        
                        if start_dt and end_dt:
                            start_formatted = start_dt.strftime("%H%M%S")
                            end_formatted = end_dt.strftime("%H%M%S")
                            dates_param = f"&dates={date_formatted}T{start_formatted}/{date_formatted}T{end_formatted}"

                final_calendar_url = f"{base_cal_url}&text={encoded_title}"
                if encoded_location:
                    final_calendar_url += f"&location={encoded_location}"
                if dates_param:
                    final_calendar_url += dates_param
                
                st.markdown("---")
                st.markdown("### 🚀 Add to Your Calendar")
                st.markdown(f'<a href="{final_calendar_url}" target="_blank"><button style="background-color:#1a73e8;color:white;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;font-size:16px;">📅 Open in Google Calendar</button></a>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"An error occurred during processing: {str(e)}")
