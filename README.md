# QuizMaster: AI-Powered Quiz Generator


*An AI-driven platform for generating, managing, and grading quizzes with real-time data.*

## Overview

QuizMaster is an innovative web application that automates the creation of multiple-choice questions (MCQs) using real-time web scraping and advanced large language models (LLMs). Built with Streamlit for a seamless user interface and MongoDB for scalable data storage, it supports three user roles—Teachers, Students, and Admins—with tailored dashboards for quiz creation, participation, and system management. Leveraging Crawl4AI for web scraping, LLaMA 3 via Groq API for question generation, and a Retrieval-Augmented Generation (RAG) pipeline with TF-IDF ranking, QuizMaster ensures high-quality, relevant quizzes. The platform automates grading, provides Plotly-based analytics, and achieves 95% question accuracy, making it a powerful tool for educational assessments.

## Features

- **Real-time Quiz Generation**: Creates MCQs from user-specified topics using web-scraped data, reflecting information as recent as 1–2 hours.
- **Role-Based Dashboards**:
  - **Teachers**: Generate, manage, and assign quizzes; view student performance analytics.
  - **Students**: Take quizzes, access practice mode, and track results with visualizations.
  - **Admins**: Perform CRUD operations on users/quizzes and monitor system analytics.
- **AI-Driven Automation**: Uses LLaMA 3 and RAG pipeline for question generation and auto-grading, with TF-IDF for content relevance.
- **Interactive Analytics**: Plotly visualizations for score distributions and performance trends.
- **Scalable Architecture**: Supports 100+ concurrent users with MongoDB and Streamlit’s session state management.

## Technologies Used

- **Frontend & Backend**: Streamlit
- **Database**: MongoDB (PyMongo)
- **Web Scraping**: Crawl4AI
- **AI & Language Models**: LLaMA 3 (Groq API), Mistral (experimental)
- **Data Processing**: scikit-learn (TF-IDF), Regex, Pandas
- **Visualization**: Plotly
- **Authentication**: bcrypt
- **Programming Language**: Python

## Installation and Setup

Follow these steps to set up QuizMaster locally. Ensure you have **Python 3.8+** installed.

### Prerequisites

- **MongoDB**: Install MongoDB Community Edition ([MongoDB Installation Guide](https://www.mongodb.com/docs/manual/installation/)).
- **Groq API Key**: Sign up at [Groq](https://groq.com/) to obtain an API key for LLaMA 3 access.
- **Crawl4AI**: Requires Python and dependencies (installed via pip).
- **Git**: For cloning the repository.

### Step-by-Step Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/[Your-GitHub-Username]/QuizMaster.git
   cd QuizMaster
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   Install required Python packages using the provided `requirements.txt` (create one if not included).
   ```bash
   pip install -r requirements.txt
   ```
   *Example `requirements.txt`:*
   ```
   streamlit==1.35.0
   pymongo==4.6.3
   groq==0.9.0
   scikit-learn==1.4.2
   plotly==5.22.0
   pandas==2.2.2
   bcrypt==4.1.3
   regex==2024.5.15
   crawl4ai==0.2.0  # Adjust version as needed
   ```

4. **Set Up MongoDB**:
   - Start MongoDB server locally:
     ```bash
     mongod
     ```
   - Create a database named `quizmaster` and collections: `users`, `quizzes`, `results`. Alternatively, the app initializes these automatically on first use.

5. **Configure Environment Variables**:
   - Create a `.env` file in the project root:
     ```
     GROQ_API_KEY=your_groq_api_key_here
     MONGODB_URI=mongodb://localhost:27017/quizmaster
     ```
   - Install `python-dotenv` and load the `.env` file in your app:
     ```bash
     pip install python-dotenv
     ```

6. **Run the Application**:
   ```bash
   streamlit run app.py
   ```
   - Open your browser to `http://localhost:8501` to access QuizMaster.

7. **Verify Setup**:
   - Register as an Admin to create users.
   - Log in as a Teacher to generate a quiz and verify MCQ output.
   - Test Student and Admin dashboards for functionality.

### Troubleshooting

- **MongoDB Connection Issues**: Ensure MongoDB is running and the `MONGODB_URI` is correct.
- **Groq API Errors**: Verify your API key and internet connection.
- **Crawl4AI Failures**: Check for updated dependencies or network restrictions.
- **Streamlit Errors**: Ensure all packages match `requirements.txt` versions to avoid compatibility issues.

## Usage

1. **Login**:
   - Access the app at `http://localhost:8501`.
   - Register or log in with credentials (bcrypt-secured).

2. **Teacher Workflow**:
   - Navigate to the Teacher Dashboard.
   - Input a topic (e.g., “Climate Change 2025”) to generate MCQs.
   - Assign quizzes to students and view analytics.

3. **Student Workflow**:
   - Access the Student Dashboard.
   - Take assigned quizzes or generate practice quizzes.
   - Review results and performance trends.

4. **Admin Workflow**:
   - Use the Admin Dashboard to manage users and quizzes.
   - Monitor system analytics and database.

## Project Structure

```
QuizMaster/
├── app.py               # Main Streamlit application
├── requirements.txt     # Python dependencies
├── .env                # Environment variables (not committed)
├── src/
│   ├── auth.py         # Authentication logic (bcrypt)
│   ├── quiz_gen.py     # Quiz generation (Crawl4AI, Groq API)
│   ├── db.py           # MongoDB interactions
│   ├── analytics.py    # Plotly visualizations
├── static/             # CSS, images (optional)
├── README.md           # Project documentation
```

## Authors

- **Jainish Gandhi**  
  GitHub: [github.com/jainishgandhi](https://github.com/jainish2594)

- **Keshini Trivedi**
  GitHub: [github.com/keshinitrivedi](https://github.com/keshinitrivedi)

---

*QuizMaster: Empowering education through AI-driven automation.*
