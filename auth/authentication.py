import bcrypt
from datetime import datetime, timedelta  # Correct import
import streamlit as st
from db.database import users_collection

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def login(username, password):
    user = users_collection.find_one({"username": username})
    if user and check_password(password, user["password"]):
        return user["role"], user["_id"]
    return None, None

def check_session_timeout():
    if "last_activity" in st.session_state:
        if datetime.now() - st.session_state.last_activity > timedelta(minutes=15):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.user_id = None
            st.warning("Session timed out due to inactivity.")
            st.rerun()
    st.session_state.last_activity = datetime.now()