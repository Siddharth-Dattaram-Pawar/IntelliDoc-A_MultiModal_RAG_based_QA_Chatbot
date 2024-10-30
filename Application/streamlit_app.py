import streamlit as st
from streamlit import session_state as ss
from streamlit_pdf_viewer import pdf_viewer
import requests
from dotenv import load_dotenv
import os
import snowflake.connector


# Load environment variables
load_dotenv()
API_URL = os.getenv("API_URL")

st.set_page_config(layout="wide")
st.title("PDF Viewer App")

import streamlit as st

st.markdown("""
<style>
    /* Set app-wide background and text colors */
    .stApp {
        background-color: black;
        color: white !important;
    }

    /* Set all heading colors to white */
    h1, h2, h3, h4, h5, h6 {
        color: white !important;
    }

    /* Set label colors for input and radio button labels */
    label, 
    .stRadio>div>label, 
    .stRadio>div>div, 
    .stRadio>div>div>label, 
    .stSelectbox label, 
    .stSubheader, 
    .stCheckbox>div {
        color: white !important;
    }

    /* Radio button option text color */
    .stRadio>div>div {
        color: white !important; /* Ensures radio button options are white */
    }

    /* Dropdown text and background colors */
    .stSelectbox>div>div>select {
        color: white !important;  /* Dropdown text color */
        background-color: #333 !important;  /* Dropdown background color */
    }

    /* Set button colors */
    .stButton>button {
        color: black;
        background-color: white;
        border: 1px solid white;
    }

    /* Set input box text and background colors */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        color: white !important; /* Input text color */
        background-color: #333 !important; /* Input background color */
    }

</style>
""", unsafe_allow_html=True)



# Helper functions
def fetch_pdf_binary(pdf_link):
    response = requests.get(pdf_link)
    if response.status_code == 200:
        return response.content
    else:
        st.error("Failed to fetch PDF.")
        return None

def fetch_summary(pdf_link):
    response = requests.post(
        f"{API_URL}/summarize",
        headers={"Authorization": f"Bearer {st.session_state['access_token']}"},
        json={"pdf_link": pdf_link}
    )
    if response.status_code == 200:
        return response.json()["summary"]
    else:
        st.error(f"Failed to fetch summary. Error: {response.json().get('detail', 'Unknown error')}")
        return None
        
# Page Functions
def registration_page():
    st.subheader("Register")
    username = st.text_input("Username", key="reg_username")
    password = st.text_input("Password", type="password", key="reg_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")

    if st.button("Register"):
        if password != confirm_password:
            st.error("Passwords do not match")
        else:
            response = requests.post(f"{API_URL}/register", json={"username": username, "password": password, "confirm_password": confirm_password})
            if response.status_code == 200:
                st.success("User registered successfully")
                st.session_state["auth_option"] = "Login"
            else:
                st.error(response.json()["detail"])

def login_page():
    st.subheader("Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        response = requests.post(f"{API_URL}/token", data={"username": username, "password": password})
        if response.status_code == 200:
            st.session_state["access_token"] = response.json()["access_token"]
            st.session_state["logged_in"] = True
            st.session_state["page"] = "main"  # Redirect to main menu after login
        else:
            st.error("Invalid credentials")

def auth_page():
    # Add dropdown to switch between login and register
    auth_option = st.selectbox("Choose action", ["Login", "Register"], key="auth_option")
    
    if auth_option == "Login":
        login_page()
    else:
        registration_page()

def main_menu():
    #st.subheader("Select an Option")
    option = st.radio("Select an Option",["View PDF and Generate Summary", "Q&A with the Bot"])
    
    if st.button("Continue"):
        if option == "View PDF and Generate Summary":
            st.session_state["page"] = "pdf_view_option"
        elif option == "Q&A with the Bot":
            st.session_state["page"] = "qa_with_bot"

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["access_token"] = None
        st.session_state["page"] = "auth"

def fetch_pdf_info_from_snowflake():
    response = requests.get(f"{API_URL}/pdfs", headers={"Authorization": f"Bearer {st.session_state['access_token']}"})
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch PDF info from the API")
        return []

def pdf_view_option():
    temp_view_type = st.radio("Choose View Type", ["Grid View", "Dropdown View"], key="view_type_radio")

    if st.button("Continue"):
        st.session_state["view_type"] = temp_view_type
        if temp_view_type == "Grid View":
            st.session_state["page"] = "pdf_list_grid_view"
        elif temp_view_type == "Dropdown View":
            st.session_state["page"] = "pdf_list_dropdown_view"

    if st.button("Back"):
        st.session_state["page"] = "main"
def pdf_list_grid_view():
    pdf_items = fetch_pdf_info_from_snowflake()
    if not pdf_items:
        st.warning("No PDFs found.")
        return

    st.subheader("Grid View")
    num_columns = 3
    for i in range(0, len(pdf_items), num_columns):
        cols = st.columns(num_columns)
        for col, item in zip(cols, pdf_items[i:i + num_columns]):
            with col:
                st.markdown(f"**{item['Title']}**")
                st.image(item['image_url'], width=100)
                if st.button("View", key=f"view_{item['Title']}"):
                    st.session_state['selected_pdf'] = item
                    st.session_state['previous_page'] = "pdf_list_grid_view"  # Store the previous page
                    st.session_state["page"] = 'pdf_detail_view'

    if st.button("Back to View Options"):
        st.session_state["page"] = "pdf_view_option"

def pdf_list_dropdown_view():
    pdf_items = fetch_pdf_info_from_snowflake()
    if not pdf_items:
        st.warning("No PDFs found.")
        return

    st.subheader("Dropdown View")
    pdf_titles = [item["Title"] for item in pdf_items]
    selected_title = st.selectbox("Select a PDF", pdf_titles)
    
    if selected_title:
        selected_item = next(item for item in pdf_items if item["Title"] == selected_title)
        st.image(selected_item['image_url'], width=150)
        st.markdown(f"**Title:** {selected_item['Title']}")
        
        if st.button("View Selected PDF"):
            st.session_state['selected_pdf'] = selected_item
            st.session_state['previous_page'] = "pdf_list_dropdown_view"  # Store the previous page
            st.session_state["page"] = 'pdf_detail_view'

    if st.button("Back to View Options"):
        st.session_state["page"] = "pdf_view_option"

def pdf_detail_view():
    if 'selected_pdf' not in st.session_state:
        st.error("No PDF selected. Please go back and select a PDF.")
        return

    item = st.session_state['selected_pdf']
    st.subheader(item['Title'])
    st.image(item['image_url'], width=200)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Preview PDF"):
            pdf_binary_data = fetch_pdf_binary(item["url"])
            if pdf_binary_data:
                with st.expander("PDF Preview", expanded=True):
                    pdf_viewer(input=pdf_binary_data, width=700, height=800)
    
    with col2:
        if st.button("Summarize PDF"):
            summary = fetch_summary(item["url"])
            if summary:
                st.markdown("### Summary")
                st.write(summary)

    if st.button("Back to PDF List"):
        if st.session_state.get('previous_page') == "pdf_list_grid_view":
            st.session_state["page"] = "pdf_list_grid_view"
        else:
            st.session_state["page"] = "pdf_list_dropdown_view"

def qa_with_bot():
    st.subheader("Q&A with the Bot")
    question = st.text_input("Ask a question about any PDF content:")
    if st.button("Submit Question"):
        if question:
            response = requests.post(
                f"{API_URL}/ask_bot",
                headers={"Authorization": f"Bearer {st.session_state['access_token']}"},
                json={"question": question}
            )
            if response.status_code == 200:
                answer = response.json().get("answer", "No answer provided.")
                st.write("Answer:", answer)
            else:
                st.error("Failed to retrieve answer from bot.")
        else:
            st.warning("Please enter a question to ask.")

    if st.button("Back"):
        st.session_state["page"] = "main"

# Main Page Navigation Logic
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "page" not in st.session_state:
    st.session_state["page"] = "auth"
if "auth_option" not in st.session_state:
    st.session_state["auth_option"] = "Login"

if not st.session_state["logged_in"]:
    auth_page()
else:
    if st.session_state["page"] == "main":
        main_menu()
    elif st.session_state["page"] == "pdf_view_option":
        pdf_view_option()
    elif st.session_state["page"] == "pdf_list_grid_view" and st.session_state.get("view_type") == "Grid View":
        pdf_list_grid_view()
    elif st.session_state["page"] == "pdf_list_dropdown_view" and st.session_state.get("view_type") == "Dropdown View":
        pdf_list_dropdown_view()
    elif st.session_state["page"] == "pdf_detail_view":
        pdf_detail_view()
    elif st.session_state["page"] == "qa_with_bot":
        qa_with_bot()