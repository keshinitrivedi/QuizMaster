import streamlit as st
from streamlit_option_menu import option_menu
from db.database import users_collection, quizzes_collection, results_collection
from auth.authentication import hash_password
from utils.analytics import plot_quiz_avg_scores

def render_quiz_preview(quiz_data, key_prefix):
    # Initialize quiz state once
    state_key = f"{key_prefix}_state"
    if state_key not in st.session_state:
        st.session_state[state_key] = {
            "questions": quiz_data,
            "reveal": [False] * len(quiz_data)  # List for per-question reveal state
        }

    quiz_state = st.session_state[state_key]

    with st.container():
        # Render each question and its correct answer expander sequentially
        for idx, q in enumerate(quiz_state["questions"]):
            with st.expander(f"Question {idx + 1}: {q['question']}", expanded=True):
                labeled_options = [f"{chr(97+i)}) {opt}" for i, opt in enumerate(q["options"])]
                for opt in labeled_options:
                    st.markdown(opt)
            # Correct answer expander after the question expander
            with st.expander(f"Show Correct Answer for Question {idx + 1}", expanded=quiz_state["reveal"][idx]):
                st.success(f"Correct Answer: {q['correct_answer']}")
                quiz_state["reveal"][idx] = True  # Update state when expanded
            # Reset reveal state if expander is collapsed
            if not st.session_state.get(f"{key_prefix}_reveal_{idx}", False):
                quiz_state["reveal"][idx] = False

    st.session_state[state_key] = quiz_state

async def admin_dashboard():
    st.title("Admin Dashboard")
    with st.sidebar:
        selected = option_menu(
            "Menu", ["Manage Users", "Manage Quizzes", "View Results", "Logout"],
            icons=["people", "book", "bar-chart", "box-arrow-right"], menu_icon="cast", default_index=0
        )

    if selected == "Logout":
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_id = None
        st.success("Logged out successfully!")
        st.rerun()

    elif selected == "Manage Users":
        st.header("Manage Users")
        with st.form(key="add_user_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["teacher", "student", "admin"])
            submit_button = st.form_submit_button(label="Add User")
        if submit_button:
            if users_collection.find_one({"username": username}):
                st.error("Username already exists.")
            else:
                users_collection.insert_one({
                    "username": username,
                    "password": hash_password(password),
                    "role": role
                })
                st.success("User added successfully!")
        
        st.subheader("Existing Users")
        for user in users_collection.find():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"Username: {user['username']}, Role: {user['role']}")
            with col2:
                if st.button(f"Delete", key=f"delete_{user['_id']}"):
                    users_collection.delete_one({"_id": user['_id']})
                    st.success(f"User {user['username']} deleted!")
                    st.rerun()

    elif selected == "Manage Quizzes":
        st.header("Manage Quizzes")
        quizzes = list(quizzes_collection.find())
        if not quizzes:
            st.info("No quizzes available.")
        else:
            quiz_options = ["Select a quiz..."] + [f"{quiz['topic']} (Created by: {users_collection.find_one({'_id': quiz['created_by']})['username']}, {quiz['date'].strftime('%Y-%m-%d %H:%M')})" for quiz in quizzes]
            selected_quiz = st.selectbox("Select a Quiz to Manage", quiz_options)
            if selected_quiz and selected_quiz != "Select a quiz...":
                selected_quiz_data = next(quiz for quiz in quizzes if f"{quiz['topic']} (Created by: {users_collection.find_one({'_id': quiz['created_by']})['username']}, {quiz['date'].strftime('%Y-%m-%d %H:%M')})" == selected_quiz)
                st.subheader(f"Quiz: {selected_quiz_data['topic']}")
                render_quiz_preview(selected_quiz_data["questions"], f"admin_view_{selected_quiz_data['_id']}")
                if st.button(f"Delete Quiz", key=f"delete_quiz_{selected_quiz_data['_id']}"):
                    try:
                        quiz_id = selected_quiz_data["_id"]
                        # Delete associated results first
                        deleted_results = results_collection.delete_many({"quiz_id": quiz_id})
                        # Delete the quiz
                        result = quizzes_collection.delete_one({"_id": quiz_id})
                        if result.deleted_count > 0:
                            st.success(f"Quiz '{selected_quiz_data['topic']}' and {deleted_results.deleted_count} associated results deleted successfully!")
                        else:
                            st.error("Failed to delete quiz: Quiz not found.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete quiz or results: {str(e)}")

    elif selected == "View Results":
        st.header("All Quiz Results")
        results = list(results_collection.find())
        if results:
            plot_quiz_avg_scores(results, users_collection)
        else:
            st.info("No results available.")