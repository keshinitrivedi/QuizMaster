async def grade_quiz(questions, user_answers):
    """
    Grade the quiz by comparing user answers (option letters) with correct answers.
    Args:
        questions: List of question dictionaries with 'correct_answer' (e.g., "A").
        user_answers: List of user-selected option letters (e.g., ["A", "B", None]).
    Returns:
        int: Number of correct answers (score).
    """
    if not questions or not user_answers or len(questions) != len(user_answers):
        return 0

    score = 0
    for question, user_answer in zip(questions, user_answers):
        if user_answer is None:
            continue
        correct_answer = question.get("correct_answer")
        if correct_answer is None:
            continue
        if isinstance(user_answer, str) and isinstance(correct_answer, str):
            if user_answer.upper() == correct_answer.upper():
                score += 1
    return score