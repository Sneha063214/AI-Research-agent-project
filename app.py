import streamlit as st
import requests
from bs4 import BeautifulSoup
import openai
from datetime import datetime
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


# ---------------------------
# CONFIG (replace with your keys)
# ---------------------------
openai.api_key = "YOUR OPENAI API KEY"
SERPAPI_KEY = "YOUR SERPAPI KEY"


# ---------------------------
# SEARCH FUNCTION (SerpAPI)
# ---------------------------
def search_serpapi(query, num_results=5):
    url = f"https://serpapi.com/search.json?q={query}&num={num_results}&api_key={SERPAPI_KEY}"
    res = requests.get(url).json()
    results = []
    for item in res.get("organic_results", []):
        results.append({"title": item.get("title"), "link": item.get("link")})
    return results


# ---------------------------
# CONTENT EXTRACTION
# ---------------------------
def extract_content(url):
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        paragraphs = " ".join([p.get_text() for p in soup.find_all("p")])
        return paragraphs[:3000]  # keep within token limit
    except Exception as e:
        return f"Error extracting content: {e}"


# ---------------------------
# SUMMARIZATION 
# ---------------------------
def summarize_text(text, query):
    if not text.strip():
        return "No extractable content."
    prompt = f"""
    Summarize the following content relevant to the query: '{query}'.
    Provide key points, facts, and insights in **bullet points**.
    If there are debates or pros/cons, include them.
    
    Content:
    {text}
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error summarizing: {e}"


# ---------------------------
# PDF EXPORT
# ---------------------------
import re
from reportlab.platypus import ListFlowable, ListItem

def clean_summary(summary: str):
    """
    Convert markdown-like bullet points into a clean list for PDF.
    """
    lines = summary.split("\n")
    bullets = []
    text = []
    for line in lines:
        line = line.strip()
        if line.startswith(("-", "*")):
            bullets.append(line.lstrip("-* ").strip())
        elif line:
            text.append(line)
    return text, bullets


def export_pdf(query, summaries):
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp_file.name, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Research Report on: {query}", styles["Title"]))
    story.append(Spacer(1, 20))

    for s in summaries:
        story.append(Paragraph(s["title"], styles["Heading2"]))
        story.append(Paragraph(f"<a href='{s['link']}'>{s['link']}</a>", styles["Normal"]))
        story.append(Spacer(1, 6))

        # Clean & format summary
        text, bullets = clean_summary(s["summary"])
        for t in text:
            story.append(Paragraph(t, styles["Normal"]))
        if bullets:
            story.append(ListFlowable(
                [ListItem(Paragraph(b, styles["Normal"])) for b in bullets],
                bulletType='bullet',
            ))

        story.append(Spacer(1, 12))

    doc.build(story)
    return tmp_file.name



# ---------------------------
#  FOR STREAMLIT APP
# ---------------------------
st.set_page_config(page_title="AI Research Agent", layout="wide")
st.title("🔎 🧐AI Research Agent")
st.image("https://media.beehiiv.com/cdn-cgi/image/fit=scale-down,format=auto,onerror=redirect,quality=80/uploads/asset/file/756e88ec-3d4d-4b37-bd39-b8ed6a0fa296/how-to-create-your-own-ai-agent-in-minutes-no-coding-needed.png?t=1730706038",width=500)
st.sidebar.header("⚙️ Settings")
num_results = st.sidebar.slider("Number of Sources", 3, 10, 5)
tone = st.sidebar.selectbox("Summary Tone", ["Academic", "Simplified", "Conversational"])




query = st.text_input("Enter your research topic:", "Recent advancements in quantum computing")
# num_results = st.slider("Number of sources to fetch", 3, 10, 5)

if st.button("Search & Summarize"):
    with st.spinner("Fetching and analyzing results..."):
        search_results = search_serpapi(query, num_results)
        
        summaries = []
        for r in search_results:
            content = extract_content(r["link"])
            summary = summarize_text(content, query)
            summaries.append({
                "title": r["title"],
                "link": r["link"],
                "summary": summary
            })
        
        # Display results
        st.subheader("📌 Research Summary")
        for s in summaries:
            st.markdown(f"### {s['title']}")
            st.markdown(f"[Source link]({s['link']})")
            st.write(s["summary"])
            st.markdown("---")
        
        # Export options
        st.subheader("📥 Export Options")
        
        # Markdown Export
        md_report = f"# Research Report on {query}\n\n"
        for s in summaries:
            md_report += f"## {s['title']}\n\n{s['summary']}\n\nSource: {s['link']}\n\n"
        st.download_button("⬇️ Download as Markdown", md_report, "report.md")
        
        # PDF Export
        pdf_path = export_pdf(query, summaries)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download as PDF", f, "report.pdf", "application/pdf")
