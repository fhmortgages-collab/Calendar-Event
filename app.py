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
            raw_pdf_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    raw_pdf_text += text + "\n"
            
            # Filter out email print/export headers (URLs, page numbers, timestamps)
            filtered_lines = []
            for line in raw_pdf_text.split('\n'):
                l_str = line.strip()
                if not l_str:
                    continue
                # Skip typical Gmail/browser print headers
                if any(noise in l_str.lower() for noise in ["http://", "https://", "page ", "mail.google.com"]):
                    continue
                if re.match(r'^\d{1,2}/\d{1,2}/\d{2},?\s*\d{1,2}:\d{2}', l_str):
                    continue
                filtered_lines.append(l_str)
            
            extracted_text = "\n".join(filtered_lines)
            st.success("Successfully extracted and cleaned text from PDF!")
        except Exception as e:
            st.error(f"Error reading PDF file: {str(e)}")

# Editable text area populated either by PDF upload or manual pasting
raw_text = st.text_area(
    "Event Details:", 
    height=180, 
    value=extracted_text if extracted_text else "",
    placeholder="Paste event text here or upload a PDF above..."
)

if st.button("Parse and Generate Calendar Link", type="primary"):
    if not raw_text.strip():
        st.error("Please provide event details via PDF upload or text pasting first.")
    else:
        with st.spinner("Extracting details..."):
            try:
                lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                
                # 1. Intelligent Title Selection
                title = "Untitled Event"
                for line in lines:
                    if "@" not in line and "http" not in line and len(line) > 5:
                        if ":" in line or "Reminder" in line or "Meeting" in line or "View" in line:
                            title = line.strip()
                            break
                if title == "Untitled Event" and lines:
                    title = lines[0]

                # 2. Extract Date (e.g., "Aug 18, 2026" or "August 18, 2026")
                date_str = ""
                date_match = re.search(r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', raw_text, re.IGNORECASE)
                if date_match:
                    date_str = date_match.group(1).replace(",", "")

                # 3. Flexible Time Range Extraction
                start_time_str, end_time_str = "", ""
                time_range_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))\s*(?:-|to)\s*(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))', raw_text, re.IGNORECASE)
                if time_range_match:
                    start_time_str = time_range_match.group(1).upper()
                    end_time_str = time_range_match.group(2).upper()

                # 4. Location Extraction
                location = ""
                loc_label_match = re.search(r'(?:location:)\s*([^\n]+)', raw_text, re.IGNORECASE)
                if loc_label_match:
                    location = loc_label_match.group(1).strip()
                else:
                    at_matches = re.findall(r'\bat\s+([A-Za-z0-9\s,\.-]+)', raw_text)
                    for match in at_matches:
                        if not re.search(r'\d{1,2}:\d{2}', match):
                            location = match.strip()
                            break

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
