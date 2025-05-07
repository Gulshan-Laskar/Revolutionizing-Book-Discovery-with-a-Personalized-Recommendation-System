# 📚 Read Your Next Favorite  
### Revolutionizing Book Discovery with a Personalized Recommendation System

## 🔍 Overview
This project tackles the challenge of personalized book discovery. Instead of relying on generic best-seller lists, we developed a dynamic recommendation system that considers user preferences, reading history, and contextual elements like mood and cultural background. The system uses scraped data from Goodreads and offers a user-friendly interface built with Streamlit.

---

## 🎯 Goal
Our objective was to build a responsive and intuitive recommendation dashboard with two main features:
1. **User-Driven Filters**: Allows users to filter recommendations by genre, author, publication year, and book length.
2. **"Find Books Like My Last Read"**: Suggests similar titles based on user input, leveraging Goodreads’ “similar books” and review data.

The success of this project was measured by:
- Accurate and relevant recommendations.
- Smooth user experience via the Streamlit dashboard.
- Scalable and clean data pipeline from ingestion to presentation.

---

## 🛠 Methodology

### 🔁 Data Pipeline
- **Ingestion**: Used Selenium and BeautifulSoup to scrape book details and reviews from Goodreads, while managing anti-bot mechanisms.
- **Storage**: Stored raw data locally before uploading to Amazon S3 and structured it with Amazon RDS for relational querying.
- **Transformation**: Applied AWS Lambda to clean, de-duplicate, and format the data automatically.
- **Serving**: Deployed an interactive web app using Streamlit to deliver the recommendations.

---

## 📊 Features

- 🎛️ Dynamic filters for custom book discovery
- 🔁 Title-based similarity recommendations
- 📈 Visual and intuitive layout with real-time suggestions
- ☁️ Hosted and powered by AWS infrastructure

---

## ⚙️ Technologies & Tools

- **Frontend & Deployment**: Streamlit, AWS EC2
- **Backend/Data Engineering**: Selenium, BeautifulSoup, Requests
- **Cloud Services**: Amazon S3, Amazon RDS, AWS Lambda
- **Data Formats**: CSV, JSON
- **Programming**: Python (pandas, re, logging, tqdm)

---

## 🧪 Challenges & Learnings

- Built advanced anti-bot workarounds using user-agent rotation and session cookie management.
- Balanced local vs. cloud-based scraping for efficiency and cost.
- Learned how to use AWS Lambda for serverless data transformation.
- Discovered the challenges of web scraping on authenticated and dynamic platforms.

---

## 📎 Demo Link

🖥️ [Live Streamlit App](http://52.20.115.45:8501/)

---

