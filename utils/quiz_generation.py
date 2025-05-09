import asyncio
import json
import re
import streamlit as st
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LXMLWebScrapingStrategy, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from groq import Groq
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result, after_log
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = "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"
groq_client = Groq(api_key=API_KEY)

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'[^A-Za-z0-9.,!?;:\'\"()\[\] ]+', '', text)
    return text.strip().lower()

def is_empty_result(result):
    """Check if the result is empty for retry logic."""
    return result is None or len(result) == 0

def after_retry_log(retry_state):
    """Log after each retry attempt and show warning only after final failure."""
    attempt = retry_state.attempt_number
    max_attempts = retry_state.retry_object.stop.max_attempt_number
    topic = retry_state.args[0]  # topic is the first argument to extract_links
    if attempt < max_attempts:
        logger.warning(f"Retry {attempt}/{max_attempts} failed for topic: {topic}")
    else:
        outcome = retry_state.outcome
        if outcome is None or (outcome.result() is None or len(outcome.result()) == 0):
            logger.warning(f"All {max_attempts} retries failed for topic: {topic}")
            st.warning(f"No external links found for topic: {topic}. Try a more specific topic.")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_result(is_empty_result),
    after=after_retry_log
)
async def extract_links(topic, max_urls: int = 15):
    """Extract relevant external links for a given topic using a broad query."""
    try:
        crawler_cfg = CrawlerRunConfig(
            exclude_domains=["youtube", "twitter", "facebook", "linkedin", "instagram"],
            cache_mode=CacheMode.BYPASS,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            #scraping_strategy=PlaywrightWebScrapingStrategy()
        )
        search_query = f"{topic}"
        url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url, config=crawler_cfg)
            if result.success:
                external_links = result.links.get("external", [])
                links = [link.get("href") for link in external_links if link.get("href") and is_valid_url(link.get("href"))]
                links = links[:max_urls]
                if links:
                    logger.info(f"Extracted {len(links)} links for topic: {topic}")
                    return links
                logger.warning(f"No external links found via crawl4ai for topic: {topic} on attempt")
                
                # Fallback: Parse raw HTML with BeautifulSoup
                logger.info(f"Attempting BeautifulSoup fallback for topic: {topic}")
                soup = BeautifulSoup(result.html, 'html.parser')
                links = []
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if href.startswith('/url?q='):
                        href = href.split('/url?q=')[1].split('&')[0]
                    if is_valid_url(href):
                        links.append(href)
                links = list(set(links))[:max_urls]
                if links:
                    logger.info(f"Extracted {len(links)} links via BeautifulSoup for topic: {topic}")
                    return links
                logger.warning(f"No external links found via BeautifulSoup for topic: {topic} on attempt")
                return []
            else:
                logger.warning(f"Failed to crawl Google search for topic: {topic} on attempt")
                return []
    except Exception as e:
        logger.error(f"Error in extract_links for topic {topic}: {str(e)}")
        st.error(f"Error crawling links for topic {topic}: {str(e)}")
        return []
    except tenacity.RetryError as e:
        logger.error(f"All retries failed for topic {topic}: {str(e)}")
        return []

def is_valid_url(url):
    """Check if a URL is valid and not excluded."""
    parsed = re.match(r'https?://[^\s]+', url)
    if not parsed:
        return False
    exclude_patterns = [
        r'\.pdf$', r'\.jpg$', r'\.png$', r'\.gif$', r'\.jpeg$',
        r'(signup | login | cart | account)'
    ]
    for pattern in exclude_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return False
    return True

async def extract_text_from_urls(urls, topic, max_text_per_source=18000, num_sources=4, chunk_size=1000, final_extract_size=6000):
    prune_filter = PruningContentFilter(threshold=0.35, threshold_type="dynamic", min_word_threshold=10)
    md_generator = DefaultMarkdownGenerator(content_filter=prune_filter)
    crawler_cfg = CrawlerRunConfig(
        exclude_external_links=True, cache_mode=CacheMode.BYPASS,
        markdown_generator=md_generator, scraping_strategy=LXMLWebScrapingStrategy(),
        excluded_tags=['form', 'header', 'footer', 'nav', 'aside']
    )
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun_many(urls, config=crawler_cfg)
        text_sources = [clean_text(result.markdown.fit_markdown)[:max_text_per_source] for result in results if result.success]
        if not text_sources:
            st.warning(f"No text extracted from URLs for topic: {topic}")
            return []
        ranked_sources = rank_chunks_tfidf(text_sources, query=topic, top_n=num_sources)
        final_texts = []
        for source in ranked_sources:
            chunks = [source[i:i+chunk_size] for i in range(0, len(source), chunk_size)]
            ranked_chunks = rank_chunks_tfidf(chunks, query=topic, top_n=final_extract_size // chunk_size)
            final_texts.append(" ".join(ranked_chunks)[:final_extract_size])
        return final_texts
    
def rank_chunks_tfidf(chunks, query, top_n):
    if not chunks:
        return []
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(chunks)
        query_vec = vectorizer.transform([query])
        cosine_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
        ranked_indices = np.argsort(cosine_similarities)[::-1][:top_n]
        return [chunks[i] for i in ranked_indices]
    except Exception as e:
        st.warning(f"TF-IDF ranking failed: {e}")
        return chunks[:top_n]

async def process_text_and_generate_questions(topic, ranked_chunk, amt):
    prompt_template = """
    Generate exactly {amt} multiple-choice questions on {topic} using the provided data: {ranked_chunk}.
    Instructions:
    - Strictly adhere to the number of questions specified.
    - The questions should be relevant to the topic and the data provided.
    - Each question should be unique and not repeated.
    - The questions should be suitable for a quiz format.
    - Each question should have a clear and concise statement of the question.
    - The options should be plausible and relevant to the question.
    - The questions should not refer to the data directly but should be based on the concepts within it.
    - Each question must have 4 distinct options with only one correct answer.
    - Format as a JSON array: [{{"question": "Text", "options": ["A", "B", "C", "D"], "correct_answer": "A"}}, ...].
    - Return ONLY the JSON array, no extra text.
    - Ensure the JSON is complete with a closing `]`.
    - Return `[]` if unable to generate questions.
    """
    final_prompt = prompt_template.format(topic=topic, ranked_chunk=ranked_chunk, amt=amt)
    try:
        quiz_completion = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": final_prompt}],
                temperature=0.7,  # Lowered for more predictable output
                max_tokens=8192,  # Reduced to fit model limit
                top_p=1,
                stream=False
            )
        )
        response_content = quiz_completion.choices[0].message.content.strip()

        # Extract JSON array and repair if incomplete
        json_match = re.search(r'\[.*', response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            if not json_str.endswith(']'):
                json_str += ']'
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            if open_braces > close_braces:
                json_str += '}' * (open_braces - close_braces)
        else:
            json_str = response_content

        questions_json = json.loads(json_str)
        if not isinstance(questions_json, list):
            st.error(f"API returned invalid format: {response_content}")
            return []
        if not questions_json:
            st.warning("No questions generated by API. Check the input data or topic.")
        return questions_json
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse quiz questions: {response_content}. Error: {e}")
        try:
            partial_json = re.findall(r'\{[^}]*"correct_answer"[^\}]*\}', response_content)
            repaired_questions = [json.loads(q + '}') if not q.endswith('}') else json.loads(q) for q in partial_json]
            if repaired_questions:
                st.warning(f"Repaired partial JSON with {len(repaired_questions)} questions.")
                return repaired_questions
            return []
        except Exception as repair_error:
            st.error(f"Repair attempt failed: {repair_error}")
            return []
    except Exception as e:
        st.error(f"Error generating quiz questions: {e}")
        return []