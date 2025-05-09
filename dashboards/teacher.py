import streamlit as st
from streamlit_option_menu import option_menu
from datetime import datetime
import time
from db.database import quizzes_collection, results_collection, users_collection
from utils.quiz_generation import extract_links, extract_text_from_urls, process_text_and_generate_questions
from utils.analytics import plot_student_avg_scores
from tenacity import RetryError

def render_quiz(quiz_data, key_prefix, interactive=False):
    # Initialize quiz state once
    state_key = f"{key_prefix}_state"
    if state_key not in st.session_state:
        st.session_state[state_key] = {
            "questions": quiz_data,
            "answers": [None] * len(quiz_data),
            "reveal": [False] * len(quiz_data),  # List for per-question reveal state
            "submitted": False
        }

    quiz_state = st.session_state[state_key]

    with st.container():
        # Render each question and its correct answer expander sequentially
        for idx, q in enumerate(quiz_state["questions"]):
            with st.expander(f"Question {idx + 1}: {q['question']}", expanded=True):
                labeled_options = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(q["options"])]
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

async def teacher_dashboard(user_id):
    st.title("Teacher Dashboard")
    with st.sidebar:
        selected = option_menu(
            "Menu", ["Generate Quiz", "View Saved Quizzes", "Share Quiz", "View Results", "Logout"],
            icons=["pencil", "book", "share", "bar-chart", "box-arrow-right"], menu_icon="cast", default_index=0
        )

    if selected == "Logout":
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_id = None
        st.success("Logged out successfully!")
        st.rerun()

    elif selected == "Generate Quiz":
        st.header("Generate a New Quiz")
        with st.form(key="generate_quiz_form"):
            topic = st.text_input("Enter the topic for quiz generation:", placeholder="e.g., React JS")
            amt = st.number_input("Number of questions:", min_value=5, max_value=20, value=5)
            submit_button = st.form_submit_button(label="Generate Quiz")
        
        if submit_button:
            if not topic.strip():
                st.error("Please enter a valid topic.")
                return
            with st.spinner("Generating quiz..."):
                try:
                    urls = await extract_links(topic)
                    if urls:
                        extracted_text = await extract_text_from_urls(urls, topic)
                        if extracted_text:
                            questions = await process_text_and_generate_questions(topic, extracted_text[0], amt)
                            if questions:
                                # Map correct answers to option letters
                                for q in questions:
                                    try:
                                        option_index = q["options"].index(q["correct_answer"])
                                        q["correct_answer"] = chr(65 + option_index)  # Convert to 'A', 'B', etc.
                                    except ValueError:
                                        st.error(f"Invalid correct answer for question: {q['question']}")
                                        return
                                key_prefix = f"preview_{topic}"
                                if f"{key_prefix}_state" in st.session_state:
                                    del st.session_state[f"{key_prefix}_state"]
                                st.session_state[f"{key_prefix}_questions"] = questions  # Store questions
                                # Automatically save the quiz to the database
                                quiz_data = {
                                    "topic": topic,
                                    "questions": questions,
                                    "created_by": user_id,
                                    "date": datetime.now(),
                                    "shared_with": []
                                }
                                quizzes_collection.insert_one(quiz_data)
                                st.success(f"Quiz '{topic}' generated and saved successfully!")
                                time.sleep(1)  # Delay to ensure DB save completes
                                st.subheader("Quiz Preview")
                                render_quiz(questions, key_prefix, interactive=False)
                            else:
                                st.error("Failed to generate quiz questions. Try a different topic or check the content source.")
                        else:
                            st.error("No valid text extracted from URLs. The sources may lack sufficient content.")
                    else:
                        st.error("No relevant URLs found for the topic. Try a more specific or different topic.")
                except (Exception, RetryError) as e:
                    st.error(f"An error occurred while generating the quiz: {str(e)}")
                    return

    elif selected == "View Saved Quizzes":
        st.header("View Saved Quizzes")
        quizzes = list(quizzes_collection.find({"created_by": user_id}))
        if not quizzes:
            st.info("No saved quizzes yet.")
        else:
            quiz_options = ["Select a quiz..."] + [f"{quiz['topic']} (Created: {quiz['date'].strftime('%Y-%m-%d %H:%M')})" for quiz in quizzes]
            selected_quiz = st.selectbox("Select a Quiz to View", quiz_options)
            if selected_quiz and selected_quiz != "Select a quiz...":
                selected_quiz_data = next(quiz for quiz in quizzes if f"{quiz['topic']} (Created: {quiz['date'].strftime('%Y-%m-%d %H:%M')})" == selected_quiz)
                st.subheader(f"Quiz: {selected_quiz_data['topic']}")
                render_quiz(selected_quiz_data["questions"], f"view_{selected_quiz_data['_id']}", interactive=False)
                if st.button("Delete Quiz", key=f"delete_{selected_quiz_data['_id']}"):
                    try:
                        quiz_id = selected_quiz_data["_id"]
                        # Delete associated results first
                        deleted_results = results_collection.delete_many({"quiz_id": quiz_id})
                        # Delete the quiz
                        result = quizzes_collection.delete_one({"_id": quiz_id, "created_by": user_id})
                        if result.deleted_count > 0:
                            st.success(f"Quiz '{selected_quiz_data['topic']}' and {deleted_results.deleted_count} associated results deleted successfully!")
                        else:
                            st.error("Failed to delete quiz: Quiz not found or unauthorized.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete quiz or results: {str(e)}")

    elif selected == "Share Quiz":
        st.header("Share a Quiz")
        quiz_options = [q["topic"] for q in quizzes_collection.find({"created_by": user_id})]
        if not quiz_options:
            st.info("No quizzes available to share.")
        else:
            quiz = st.selectbox("Select Quiz to Share", quiz_options)
            students = users_collection.find({"role": "student"})
            student_options = [s["username"] for s in students]
            selected_students = st.multiselect("Select Students", student_options)
            if st.button("Share Quiz"):
                quiz_data = quizzes_collection.find_one({"topic": quiz, "created_by": user_id})
                if quiz_data:
                    for student in selected_students:
                        student_id = users_collection.find_one({"username": student})["_id"]
                        quizzes_collection.update_one(
                            {"_id": quiz_data["_id"]},
                            {"$addToSet": {"shared_with": student_id}}
                        )
                    st.success(f"Quiz '{quiz}' shared with {len(selected_students)} student(s)!")
                else:
                    st.error("Quiz not found.")

    elif selected == "View Results":
        st.header("Quiz Results")
        results = list(results_collection.find({"teacher_id": user_id}))
        if results:
            plot_student_avg_scores(results, users_collection)
        else:
            st.info("No quiz results available yet.")