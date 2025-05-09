import pandas as pd
import plotly.express as px
import streamlit as st

def plot_student_avg_scores(results, users_collection):
    df = pd.DataFrame([
        {
            "Student": users_collection.find_one({"_id": r["student_id"]})["username"],
            "Quiz": r["quiz_topic"],
            "Score": r["score"],
            "Date": r["date"]
        } for r in results
    ])
    if not df.empty:
        st.dataframe(df)
        avg_scores = df.groupby("Student")["Score"].mean().reset_index()
        fig = px.bar(avg_scores, x="Student", y="Score", title="Average Scores per Student")
        st.plotly_chart(fig)
    else:
        st.info("No results available.")

def plot_student_score_trend(results):
    df = pd.DataFrame([
        {"Quiz": r["quiz_topic"], "Score": r["score"], "Date": r["date"]}
        for r in results
    ])
    if not df.empty:
        st.dataframe(df)
        df["Date"] = pd.to_datetime(df["Date"])
        fig = px.line(df, x="Date", y="Score", title="Score Trend", markers=True)
        st.plotly_chart(fig)
    else:
        st.info("No results available.")

def plot_quiz_avg_scores(results, users_collection):
    df = pd.DataFrame([
        {
            "Student": users_collection.find_one({"_id": r["student_id"]})["username"],
            "Quiz": r["quiz_topic"],
            "Score": r["score"],
            "Date": r["date"]
        } for r in results
    ])
    if not df.empty:
        st.dataframe(df)
        avg_scores = df.groupby("Quiz")["Score"].mean().reset_index()
        fig = px.bar(avg_scores, x="Quiz", y="Score", title="Average Scores per Quiz")
        st.plotly_chart(fig)
    else:
        st.info("No results available.")