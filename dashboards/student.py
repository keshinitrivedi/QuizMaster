import streamlit as st
from streamlit_option_menu import option_menu
from datetime import datetime
from db.database import quizzes_collection, results_collection
from utils.quiz_generation import extract_links, extract_text_from_urls, process_text_and_generate_questions
from utils.quiz_grading import grade_quiz
from utils.analytics import plot_student_score_trend
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def render_quiz(quiz_data, key_prefix, interactive=True, previous_answers=None):
    state_key = key_prefix  # Use key_prefix directly as state_key
    if state_key not in st.session_state:
        st.session_state[state_key] = {
            "questions": quiz_data,
            "answers": previous_answers if previous_answers else [None] * len(quiz_data),
            "submitted": bool(previous_answers),
            "reveal": [False] * len(quiz_data)
        }

    quiz_state = st.session_state[state_key]

    with st.container():
        if interactive and not quiz_state["submitted"]:
            with st.form(key=f"{key_prefix}_quiz_form"):
                for idx, q in enumerate(quiz_state["questions"]):
                    with st.expander(f"Question {idx + 1}: {q['question']}", expanded=True):
                        labeled_options = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(q["options"])]
                        selected_option = st.radio(
                            "Select an option:",
                            options=[chr(65+i) for i in range(len(q["options"]))],
                            format_func=lambda x: next(opt for opt in labeled_options if opt.startswith(f"{x})")),
                            key=f"{key_prefix}_q{idx}",
                            index=None if quiz_state["answers"][idx] is None else ord(quiz_state["answers"][idx]) - 65 if quiz_state["answers"][idx] else None,
                            disabled=quiz_state["submitted"]
                        )
                        quiz_state["answers"][idx] = selected_option
                submit_quiz = st.form_submit_button("Submit Quiz")
                if submit_quiz:
                    if None in quiz_state["answers"]:
                        st.error("Please answer all questions before submitting.")
                        return None
                    quiz_state["submitted"] = True
                    st.session_state[state_key] = quiz_state
                    return quiz_state["answers"]
        else:
            for idx, q in enumerate(quiz_state["questions"]):
                with st.expander(f"Question {idx + 1}: {q['question']}", expanded=True):
                    labeled_options = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(q["options"])]
                    for opt in labeled_options:
                        st.markdown(opt)
                    if quiz_state["answers"][idx] is not None:
                        st.markdown(f"**Your Answer**: {quiz_state['answers'][idx]}")
                with st.expander(f"Show Correct Answer for Question {idx + 1}", expanded=quiz_state.get("reveal", [False])[idx]):
                    st.success(f"Correct Answer: {q['correct_answer']}")
                    quiz_state.setdefault("reveal", [False] * len(quiz_data))[idx] = True
                if not st.session_state.get(f"{key_prefix}_reveal_{idx}", False):
                    quiz_state.setdefault("reveal", [False] * len(quiz_data))[idx] = False

    st.session_state[state_key] = quiz_state
    return quiz_state["answers"]

async def student_dashboard(user_id):
    st.title("Student Dashboard")
    with st.sidebar:
        selected = option_menu(
            "Menu", ["Take Quiz", "View Results", "Practice Quiz", "Logout"],
            icons=["pencil-square", "bar-chart", "book", "box-arrow-right"], menu_icon="cast", default_index=0
        )

    if selected == "Logout":
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_id = None
        st.success("Logged out successfully!")
        st.rerun()

    elif selected == "Take Quiz":
        st.header("Take a Quiz")
        quizzes = list(quizzes_collection.find({"shared_with": user_id}))
        quiz_options = [q["topic"] for q in quizzes]
        if not quiz_options:
            st.info("No quizzes assigned to you yet.")
        else:
            quiz = st.selectbox("Select a Quiz", quiz_options)
            if quiz:
                quiz_data = quizzes_collection.find_one({"topic": quiz})
                key_prefix = f"take_{quiz}_{user_id}"
                previous_result = results_collection.find_one({"student_id": user_id, "quiz_topic": quiz})
                if previous_result:
                    st.info(f"You have already taken this quiz.")
                    st.success(f"Your previous score: {int(previous_result['score'] * len(quiz_data['questions']) / 100)}/{len(quiz_data['questions'])} ({previous_result['score']:.2f}%)")
                    previous_answers = previous_result.get("answers", [None] * len(quiz_data["questions"]))
                    st.subheader(f"Quiz: {quiz}")
                    render_quiz(quiz_data["questions"], key_prefix, interactive=False, previous_answers=previous_answers)
                else:
                    if st.button("Start Quiz", key=f"start_{quiz}_{user_id}"):
                        # Clear any existing state to ensure fresh initialization
                        if key_prefix in st.session_state:
                            del st.session_state[key_prefix]
                        # Render quiz directly, state will be initialized in render_quiz
                        st.session_state[f"{key_prefix}_start"] = True
                    
                    if st.session_state.get(f"{key_prefix}_start", False):
                        st.subheader(f"Quiz: {quiz}")
                        user_answers = render_quiz(quiz_data["questions"], key_prefix, interactive=True)
                        if st.session_state[key_prefix]["submitted"]:
                            with st.spinner("Grading quiz..."):
                                try:
                                    logger.info(f"Grading quiz for student_id: {user_id}, quiz: {quiz}")
                                    score = await grade_quiz(quiz_data["questions"], user_answers)
                                    if score is None or score < 0:
                                        raise ValueError("Invalid score returned by grading function")
                                    total = len(quiz_data["questions"])
                                    percentage = (score / total) * 100 if total > 0 else 0
                                    result_doc = {
                                        "student_id": user_id,
                                        "quiz_id": quiz_data["_id"],
                                        "quiz_topic": quiz,
                                        "score": percentage,
                                        "teacher_id": quiz_data["created_by"],
                                        "date": datetime.now(),
                                        "answers": user_answers
                                    }
                                    logger.info(f"Saving result: {result_doc}")
                                    results_collection.insert_one(result_doc)
                                    st.success(f"Your score: {score}/{total} ({percentage:.2f}%)")
                                    # Clear session state to prevent reuse
                                    if key_prefix in st.session_state:
                                        del st.session_state[key_prefix]
                                    if f"{key_prefix}_start" in st.session_state:
                                        del st.session_state[f"{key_prefix}_start"]
                                except Exception as e:
                                    logger.error(f"Grading failed for student_id: {user_id}, quiz: {quiz}, error: {str(e)}")
                                    st.error(f"Grading failed: {str(e)}")
                                    score = 0
                            st.info("Quiz submitted. Review your answers above.")
                            render_quiz(quiz_data["questions"], key_prefix, interactive=False)

    elif selected == "View Results":
        st.header("Your Quiz Results")
        results = list(results_collection.find({"student_id": user_id}))
        if results:
            plot_student_score_trend(results)
        else:
            st.info("No results available yet.")

    elif selected == "Practice Quiz":
        st.header("Practice Quiz")
        with st.form(key="practice_quiz_form"):
            topic = st.text_input("Enter topic for practice quiz:", placeholder="e.g., Python Basics")
            amt = st.number_input("Number of questions:", min_value=5, max_value=20, value=5)
            submit_button = st.form_submit_button(label="Generate Practice Quiz")
        
        if submit_button:
            with st.spinner("Generating practice quiz..."):
                urls = await extract_links(topic)
                if urls:
                    extracted_text = await extract_text_from_urls(urls, topic)
                    if extracted_text:
                        questions = await process_text_and_generate_questions(topic, extracted_text[0], amt)
                        if questions:
                            valid_questions = []
                            for q in questions:
                                if q.get("correct_answer") and q.get("options") and q["correct_answer"] in q["options"]:
                                    option_index = q["options"].index(q["correct_answer"])
                                    q["correct_answer"] = chr(65 + option_index)
                                    valid_questions.append(q)
                                else:
                                    logger.warning(f"Invalid question format for topic {topic}: {q.get('question', 'Unknown')}, correct_answer: {q.get('correct_answer', 'Missing')}")
                            if not valid_questions:
                                st.error("No valid questions generated. Try a different topic.")
                                return
                            # Use user_id in key_prefix
                            key_prefix = f"practice_{topic}_{user_id}"
                            if key_prefix in st.session_state:
                                del st.session_state[key_prefix]
                            st.session_state[key_prefix + "_questions"] = valid_questions
                            st.session_state[key_prefix + "_start"] = True
                        else:
                            st.error("Failed to generate practice quiz questions.")
                    else:
                        st.error("No valid text extracted from URLs.")
                else:
                    st.error("No relevant URLs found.")
        
        key_prefix = f"practice_{topic}_{user_id}"
        if st.session_state.get(key_prefix + "_start", False):
            questions = st.session_state.get(key_prefix + "_questions", [])
            if questions:
                st.subheader(f"Practice Quiz: {topic}")
                user_answers = render_quiz(questions, key_prefix, interactive=True)
                if st.session_state[key_prefix]["submitted"]:
                    with st.spinner("Grading quiz..."):
                        try:
                            logger.info(f"Grading practice quiz for student_id: {user_id}, topic: {topic}")
                            score = await grade_quiz(questions, user_answers)
                            if score is None or score < 0:
                                raise ValueError("Invalid score returned by grading function")
                            total = len(questions)
                            percentage = (score / total) * 100 if total > 0 else 0
                            st.success(f"Your score: {score}/{total} ({percentage:.2f}%)")
                            # Clear session state
                            if key_prefix in st.session_state:
                                del st.session_state[key_prefix]
                            if key_prefix + "_questions" in st.session_state:
                                del st.session_state[key_prefix + "_questions"]
                            if key_prefix + "_start" in st.session_state:
                                del st.session_state[key_prefix + "_start"]
                        except Exception as e:
                            logger.error(f"Grading failed for student_id: {user_id}, topic: {topic}, error: {str(e)}")
                            st.error(f"Grading failed: {str(e)}")
                            score = 0
                    st.info("Quiz submitted. Review your answers above.")
                    render_quiz(questions, key_prefix, interactive=False)