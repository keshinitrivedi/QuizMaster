import asyncio
import streamlit as st
from datetime import datetime
from auth.authentication import login, check_session_timeout
from dashboards.teacher import teacher_dashboard
from dashboards.student import student_dashboard
from dashboards.admin import admin_dashboard

def render_login_page():
    st.title("QuizMaster Login")
    st.markdown("### Welcome to QuizMaster")
    
    with st.form(key="login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button(label="Login")
        
        if submit_button:
            role, user_id = login(username, password)
            if role:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.session_state.user_id = user_id
                st.session_state.last_activity = datetime.now()
                st.success(f"Logged in as {role}")
                st.rerun()
            else:
                st.error("Invalid credentials")

async def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_id = None
        st.session_state.last_activity = datetime.now()

    if not st.session_state.logged_in:
        render_login_page()
    else:
        check_session_timeout()
        if st.session_state.role == "teacher":
            await teacher_dashboard(st.session_state.user_id)
        elif st.session_state.role == "student":
            await student_dashboard(st.session_state.user_id)
        elif st.session_state.role == "admin":
            await admin_dashboard()
        else:
            st.error("Invalid role detected. Please log in again.")
            st.session_state.logged_in = False
            st.rerun()

if __name__ == "__main__":
    import sys
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    st.set_page_config(page_title="QuizMaster", layout="wide", initial_sidebar_state="expanded")
    # Let Streamlit handle the async execution
    asyncio.run(main()) # Schedule main() in the existing loop