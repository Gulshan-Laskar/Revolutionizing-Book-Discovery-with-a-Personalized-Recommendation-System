# %pip install webdriver-manager requests beautifulsoup4 tqdm selenium         # install required packages


import os
import time
import random
import re
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import csv
from tqdm import tqdm
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper_log.txt"),
        logging.StreamHandler()
    ]
)

# Configuration
BASE_URL = 'https://www.goodreads.com'
CSV_FILE = 'books_data_full.csv'
JSON_FILE = 'books_data_full.json'  # Added JSON file path
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
# Add a list of random agents
AGENTS_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
]

def selenium_login():
    """Login and return cookies"""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(f"{BASE_URL}/user/sign_in")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Sign in')]"))
        )
        driver.find_element(By.XPATH, "//button[contains(., 'Sign in with email')]").click()
        
        # Fill credentials
        driver.find_element(By.ID, "ap_email").send_keys(os.getenv('GOODREADS_EMAIL', 'rowdygamer2002@gmail.com'))   #add username
        driver.find_element(By.ID, "ap_password").send_keys(os.getenv('GOODREADS_PASSWORD', 'LucyLove@6688'))   # add password
        driver.find_element(By.ID, "signInSubmit").click()
        
        # Verify login
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/sign_out']"))
        )
        return {c['name']: c['value'] for c in driver.get_cookies()}
    
    finally:
        driver.quit()

def clean_number(text):
    """Extract numbers from text"""
    return re.sub(r"[^\d]", "", text) if text else '0'

def get_reviewer_info(review_soup):
    """Extract reviewer details from review card"""
    try:
        name = review_soup.select_one('div.ReviewerProfile__name').text.strip()
        meta = review_soup.select_one('div.ReviewerProfile__meta').text
        followers = re.search(r'(\d+[\d.k]+)\s+followers', meta)
        return {
            'name': name,
            'followers': followers.group(1) if followers else 'N/A',
            'reviews': clean_number(re.search(r'(\d+)\s+reviews', meta).group(1))
        }
    except Exception as e:
        return {'name': 'N/A', 'followers': 'N/A', 'reviews': '0'}

def scrape_book_page(session, book_url, max_retries=3):
    """Scrape detailed book information with retry mechanism"""
    retries = 0
    while retries < max_retries:
        try:
            # Randomize user agent for this request
            session.headers['User-Agent'] = random.choice(AGENTS_LIST)
            response = session.get(book_url, timeout=10)
            
            if response.status_code != 200:
                logging.error(f"Failed to get {book_url}. Status code: {response.status_code}")
                retries += 1
                time.sleep(2 * retries)  # Exponential backoff
                continue
                
            soup = BeautifulSoup(response.text, 'lxml')

            # Detect anti-scraping measures or login redirect
            if "human verification" in response.text.lower() or "captcha" in response.text.lower():
                logging.error("Anti-bot measures detected. Waiting longer before retry.")
                time.sleep(20)  # Wait longer if anti-bot measures detected
                retries += 1
                continue

            # Rest of the function remains the same
            book_data = {
                'title': '',
                'author': '',
                'rating': '',
                'ratings_count': '0',
                'reviews_count': '0',
                'genres': [],
                'description': '',
                'reviews': [],
                'author_meta': {'name': 'N/A', 'books': '0', 'followers': '0', 'description': 'N/A'}
            }

            try:
                # Basic info
                book_data['title'] = soup.select_one('h1[data-testid="bookTitle"]').text.strip()
                book_data['author'] = soup.select_one('span.ContributorLink__name').text.strip()
                book_data['rating'] = soup.select_one('div.RatingStatistics__rating').text.strip()
                
                # Replace rating extraction with a combined selector:
                ratings_element = soup.select_one('span[data-testid="ratingsCount"], span.count')
                if ratings_element:
                    book_data['ratings_count'] = clean_number(ratings_element.get_text())

                reviews_element = soup.select_one('span[data-testid="reviewsCount"], span.count')
                if reviews_element:
                    book_data['reviews_count'] = clean_number(reviews_element.get_text())

                # Genres: remove limit to 10
                book_data['genres'] = [
                    genre.text.strip() 
                    for genre in soup.select('span.BookPageMetadataSection__genreButton')
                ]
                
                # Description
                description = soup.select_one('span.Formatted')
                if description:
                    book_data['description'] = ' '.join(description.stripped_strings)[:500] + "..."
                
                # Reviews: remove slice so all reviews are captured
                review_cards = soup.select('article.ReviewCard')
                for review in review_cards:
                    try:
                        review_data = {
                            'author': get_reviewer_info(review),
                            'text': review.select_one('section.ReviewText').text.strip(),
                            'rating': len(review.select('span.RatingStar--active'))
                        }
                        book_data['reviews'].append(review_data)
                    except Exception as e:
                        continue

                # Author meta
                about_author_section = soup.select_one('div.FeaturedPerson__infoPrimary')
                if about_author_section:
                    # Name
                    book_data['author_meta']['name'] = book_data['author']
                    # Books & followers
                    stats_text = about_author_section.select_one('span.Text__body3.Text__subdued')
                    if stats_text:
                        match = re.search(r'(\d+(\.\d+)?k?)\s*books.*?(\d+(\.\d+)?k?)\s*followers', stats_text.get_text(strip=True), re.IGNORECASE)
                        if match:
                            book_data['author_meta']['books'] = match.group(1)
                            book_data['author_meta']['followers'] = match.group(3)
                # Description
                desc_el = soup.select_one('div.DetailsLayoutRightParagraph span.Formatted')
                if desc_el:
                    book_data['author_meta']['description'] = ' '.join(desc_el.stripped_strings)[:300] + '...'
                
            except Exception as e:
                print(f"Error scraping {book_url}: {str(e)}")
            
            # Log successful scrape
            logging.info(f"Successfully scraped book: {book_url}")
            return book_data
            
        except Exception as e:
            logging.error(f"Error scraping {book_url}: {str(e)}")
            retries += 1
            time.sleep(2 * retries)  # Exponential backoff
    
    # If all retries fail, return empty data
    logging.error(f"All retries failed for {book_url}")
    return {
        'title': 'Failed to scrape',
        'author': 'N/A',
        'rating': '0',
        'ratings_count': '0',
        'reviews_count': '0',
        'genres': [],
        'description': 'Failed to scrape',
        'reviews': [],
        'author_meta': {'name': 'N/A', 'books': '0', 'followers': '0', 'description': 'N/A'}
    }

def load_json_data():
    """Load existing JSON data or return empty dict"""
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON data: {e}")
    return {"books": {}}  # Initialize with empty books dictionary

def save_book_to_json(book_data, json_data):
    """Add book data to JSON and save the file"""
    book_id = book_data.get('book_id')
    if book_id:
        json_data["books"][book_id] = book_data
        try:
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2)
        except Exception as e:
            print(f"Error saving JSON data: {e}")

def scrape_books(cookies):
    """Main scraping function"""
    session = requests.Session()
    session.headers.update(HEADERS)
    session.cookies.update(cookies)

    # Load JSON data for faster book ID lookups
    json_data = load_json_data()
    
    # Get already scraped Book IDs from JSON
    scraped_ids = set(json_data["books"].keys())
    
    # Double-check with CSV if JSON is empty or newly created
    if not scraped_ids and os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'Book ID' in row and row['Book ID']:
                        scraped_ids.add(row['Book ID'])
                        # If book exists in CSV but not in JSON, add a placeholder
                        if row['Book ID'] not in json_data["books"]:
                            json_data["books"][row['Book ID']] = {
                                "book_id": row['Book ID'],
                                "title": row.get('Title', ''),
                                "author": row.get('Author', '')
                            }
        except Exception as e:
            print(f"Error reading CSV: {e}")

    # Open CSV file in append mode if exists, else write header with "Book ID"
    file_exists = os.path.exists(CSV_FILE)
    csv_mode = 'a' if file_exists else 'w'
    with open(CSV_FILE, csv_mode, newline='', encoding='utf-8') as f:
        fieldnames = ['Book ID', 'Title', 'Author', 'Rating', 'Ratings Count', 'Reviews Count',
                      'Genres', 'Description', 'Reviews (JSON)', 'Author Info (JSON)']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        page = 1
        empty_page_count = 0
        max_empty_pages = 3  # Stop after this many consecutive empty pages
        max_pages = 25  # Set a reasonable limit to avoid infinite loops
        
        while page <= max_pages:
            logging.info(f"Scraping page {page}")
            try:
                # Randomize agent for each page request
                session.headers['User-Agent'] = random.choice(AGENTS_LIST)
                url = f"{BASE_URL}/shelf/show/popular?page={page}"
                
                # Add error handling for the page request
                try:
                    response = session.get(url, timeout=10)
                    if response.status_code != 200:
                        logging.error(f"Failed to get page {page}. Status code: {response.status_code}")
                        if response.status_code == 429:  # Too Many Requests
                            logging.info(f"Rate limited. Waiting 60 seconds before retry.")
                            time.sleep(60)
                            continue
                        elif response.status_code >= 500:  # Server error
                            logging.info(f"Server error. Waiting 30 seconds before retry.")
                            time.sleep(30)
                            continue
                        else:
                            # For other errors, increment empty page count
                            empty_page_count += 1
                except requests.RequestException as e:
                    logging.error(f"Request error on page {page}: {str(e)}")
                    time.sleep(5)
                    continue
                
                # Check for anti-scraping measures
                if "human verification" in response.text.lower() or "captcha" in response.text.lower():
                    logging.error(f"Anti-bot measures detected on page {page}. Waiting 60 seconds.")
                    time.sleep(60)
                    continue
                
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Try various selectors to find books
                books = soup.select('a.bookTitle[href*="/book/show/"]')
                if not books:
                    books = soup.select('div.BookCard__titleWithSubtitle a')
                if not books:
                    books = soup.select('a[href*="/book/show/"]')
                
                logging.info(f"Found {len(books)} books on page {page}")
                
                if not books:
                    empty_page_count += 1
                    logging.warning(f"No books found on page {page}. Empty page count: {empty_page_count}")
                    if empty_page_count >= max_empty_pages:
                        logging.info(f"Reached {max_empty_pages} consecutive empty pages. Stopping.")
                        break
                    page += 1
                    time.sleep(5)  # Wait longer between empty pages
                    continue
                else:
                    empty_page_count = 0  # Reset empty page counter since we found books
                
                for book in tqdm(books, desc=f"Scraping books on page {page}", leave=True):
                    # Extract Book ID from the URL (e.g. /book/show/12345-some-slug)
                    href = book.get('href', '')
                    if not href:
                        continue
                        
                    match = re.search(r'/book/show/(\d+)', href)
                    if match:
                        book_id = match.group(1)
                    else:
                        continue  # skip if we cannot extract an ID
                    
                    if book_id not in scraped_ids:
                        book_url = BASE_URL + href if href.startswith('/') else href
                        try:
                            book_data = scrape_book_page(session, book_url)
                            book_data['book_id'] = book_id
                            
                            # Write to CSV
                            writer.writerow({
                                'Book ID': book_id,
                                'Title': book_data['title'],
                                'Author': book_data['author'],
                                'Rating': book_data['rating'],
                                'Ratings Count': book_data['ratings_count'],
                                'Reviews Count': book_data['reviews_count'],
                                'Genres': ', '.join(book_data['genres']),
                                'Description': book_data['description'],
                                'Reviews (JSON)': json.dumps(book_data['reviews']),
                                'Author Info (JSON)': json.dumps(book_data['author_meta'])
                            })
                            f.flush()  # persist data instantly
                            
                            # Save to JSON
                            save_book_to_json(book_data, json_data)
                            
                            scraped_ids.add(book_id)
                            logging.info(f"Saved book: {book_data['title']} (ID: {book_id})")
                        except Exception as e:
                            logging.error(f"Error processing book {book_id}: {e}")
                        
                        # Variable delay between requests to avoid detection
                        time.sleep(random.uniform(0.5, 1.5))
                    else:
                        logging.info(f"Skipping Book ID {book_id} (already scraped)")
                
                page += 1
                # Random delay between pages
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                logging.error(f"Error processing page {page}: {str(e)}")
                time.sleep(5)
                page += 1  # Move to next page despite error
    
        logging.info(f"Scraping completed after processing {page-1} pages.")
    
    # Ensure final JSON data is saved
    try:
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving final JSON data: {e}")

def main():
    try:
        logging.info("Starting the scraping process")
        cookies = selenium_login()
        scrape_books(cookies)
        logging.info(f"Scraping completed! Data saved to {CSV_FILE} and {JSON_FILE}")
    except Exception as e:
        logging.error(f"Fatal error in main: {str(e)}")

if __name__ == "__main__":
    main()