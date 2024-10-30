import streamlit as st
from streamlit import session_state as ss
from streamlit_pdf_viewer import pdf_viewer
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_URL = os.getenv("API_URL")

st.set_page_config(layout="wide")

st.title("PDF Viewer App")


# Registration page
def registration_page():
    st.subheader("Register")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
 
    if st.button("Register"):
        if password != confirm_password:
            st.error("Passwords do not match")
        else:
            response = requests.post(f"{API_URL}/register", json={"username": username, "password": password, "confirm_password": confirm_password})
            if response.status_code == 200:
                st.success("User registered successfully")
            else:
                st.error(response.json()["detail"])
 
# Login page
def login_page():
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
 
    if st.button("Login"):
        response = requests.post(f"{API_URL}/token", data={"username": username, "password": password})
        if response.status_code == 200:
            st.session_state["access_token"] = response.json()["access_token"]
            st.session_state["logged_in"] = True  # Set the logged in flag
            st.success("Logged in successfully")
            st.rerun()  # Refresh the page to show the documents selection
        else:
            st.error("Invalid credentials")
 
# Image grid view
def image_view():
    response = requests.get(f"{API_URL}/images", headers={"Authorization": f"Bearer {st.session_state['access_token']}"})
   
    if response.status_code != 200:
        st.error("Failed to fetch images.")
        return
 
    images = response.json()
    if not images:
        st.warning("No images found.")
        return
 
    cols = st.columns(3)
    for idx, image in enumerate(images):
        image_url = image["url"]
        image_name = image["key"].split("/")[-1]  # Get only the file name without the folder path
        with cols[idx % 3]:
            st.image(image_url, use_column_width=True, caption=image_name)

# Helper function to fetch PDF as binary data from S3
def fetch_pdf_binary(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        st.error("Failed to fetch PDF.")
        return None
    
def fetch_summary(file_key):
    response = requests.post(
        f"{API_URL}/summarize",
        headers={"Authorization": f"Bearer {st.session_state['access_token']}"},
        json={"file_key": file_key}
    )
    if response.status_code == 200:
        return response.json()["summary"]
    else:
        st.error(f"Failed to fetch summary. Error: {response.json().get('detail', 'Unknown error')}")
        return None

def pdf_view(view_type):
    # Fetch PDFs
    pdfs_response = requests.get(f"{API_URL}/pdfs", headers={"Authorization": f"Bearer {st.session_state['access_token']}"}).json()
    if not pdfs_response:
        st.warning("No PDFs found.")
        return

    pdf_items = [{"title": pdf["key"].split("/")[-1].replace(".pdf", ""), "url": pdf["url"]} for pdf in pdfs_response]


    if view_type == "Grid View":
        # Display PDFs in a grid format
        num_columns = 2
        for i in range(0, len(pdf_items), num_columns):
            cols = st.columns(num_columns)
            for col, item in zip(cols, pdf_items[i:i + num_columns]):
                with col:
                    st.markdown(f"### {item['title']}")
                    if st.button("Preview", key=f"preview_{item['title']}"):
                        pdf_binary_data = fetch_pdf_binary(item["url"])
                        if pdf_binary_data:
                            with st.expander("PDF Preview", expanded=True):
                                pdf_viewer(input=pdf_binary_data, width=700, height=800)  # Scrollable container
                    if st.button("Summarize", key=f"summarize_{item['title']}"):
                        summary = fetch_summary(f"{item['title']}.pdf")
                        if summary:
                            st.markdown("### Summary")
                            st.write(summary)

    elif view_type == "Dropdown View":
        # Display PDFs in a dropdown selection format
        pdf_titles = [item["title"] for item in pdf_items]
        pdf_selected_title = st.selectbox("Select a PDF to view", pdf_titles)
        
        if pdf_selected_title:
            selected_item = next(item for item in pdf_items if item["title"] == pdf_selected_title)
            st.markdown(f"### {selected_item['title']}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Preview Selected PDF"):
                    pdf_binary_data = fetch_pdf_binary(selected_item["url"])
                    if pdf_binary_data:
                        with st.expander("PDF Preview", expanded=True):
                            pdf_viewer(input=pdf_binary_data, width=700, height=800)  # Scrollable container
            with col2:
                if st.button("Summarize Selected PDF"):
                    summary = fetch_summary(f"{selected_item['title']}.pdf")
                    if summary:
                        st.markdown("### Summary")
                        st.write(summary)

# Display login or registration page if not logged in
if "access_token" not in st.session_state:
    page = st.selectbox("Choose", ["Login", "Register"])
    if page == "Login":
        login_page()
    else:
        registration_page()
else:
    if st.session_state.get("logged_in", False):
        view_type = st.radio("Choose View", ["Grid View", "Dropdown View"])
        pdf_view(view_type)