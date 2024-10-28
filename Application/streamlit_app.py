import streamlit as st 
import requests
import os
from dotenv import load_dotenv
 
# Load environment variables
load_dotenv()
API_URL = os.getenv("API_URL")
 
st.title("Login and Registration App")
 
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
        image_url = image["url"]  # Use the pre-signed URL for direct access to the image
        with cols[idx % 3]:
            st.image(image_url, use_column_width=True, caption=image['key'])
           
# PDF dropdown view
def pdf_view():
    response = requests.get(f"{API_URL}/pdfs", headers={"Authorization": f"Bearer {st.session_state['access_token']}"})
   
    if response.status_code != 200:
        st.error("Failed to fetch PDFs.")
        return
   
    pdfs = response.json()
    if not pdfs:
        st.warning("No PDFs found.")
        return
 
    pdf_selected = st.selectbox("Select PDF", [pdf["key"] for pdf in pdfs])
 
    if st.button("Summarize PDF"):
        response = requests.post(f"{API_URL}/summarize", headers={"Authorization": f"Bearer {st.session_state['access_token']}"}, json={"file_key": pdf_selected})
        if response.status_code == 200:
            st.write(response.json()["summary"])
        else:
            st.error("Failed to summarize PDF.")
 
# Display login or registration page if not logged in
if "access_token" not in st.session_state:
    page = st.selectbox("Choose", ["Login", "Register"])
    if page == "Login":
        login_page()
    else:
        registration_page()
else:
    if st.session_state.get("logged_in", False):
        option = st.radio("Select Option", ["View Images", "View PDFs"])
        if option == "View Images":
            image_view()
        else:
            pdf_view()