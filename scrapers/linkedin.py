import requests
from bs4 import BeautifulSoup
import time
import sys

class LinkedInScraper:
    def __init__(self, delay=2):
        self.delay = delay
        self.max_retries = 3
        self.backoff_factor = 2

    def _retry_request(self, url, headers, timeout=10):
        """Retry request with exponential backoff on 429"""
        for attempt in range(self.max_retries):
            try:
                resp = requests.get(url, headers=headers, timeout=timeout)
                if resp.status_code == 429:
                    wait_time = (self.backoff_factor ** attempt) * 10
                    print(f"⏸️  Rate limited (429). Waiting {wait_time}s before retry...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = (self.backoff_factor ** attempt) * 5
                print(f"⚠️  Request failed: {e}. Retrying in {wait_time}s...", file=sys.stderr)
                time.sleep(wait_time)
        return None

    def search(self, keywords: str, location: str, max_results: int = 100) -> list:
        all_jobs = []
        seen_urls = set()
        start_offset = 0
        consecutive_empty_pages = 0
        max_empty_pages = 3

        while len(all_jobs) < max_results:
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keywords}&location={location}&start={start_offset}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            try:
                resp = self._retry_request(url, headers)
                if resp is None:
                    break
                time.sleep(self.delay)
                soup = BeautifulSoup(resp.text, 'html.parser')
                jobs_html = soup.find_all('li')
                if not jobs_html:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= max_empty_pages:
                        break
                    start_offset += 10
                    continue
                consecutive_empty_pages = 0

                for job_html in jobs_html:
                    title_tag = job_html.find('h3', class_='base-search-card__title')
                    company_tag = job_html.find('h4', class_='base-search-card__subtitle')
                    location_tag = job_html.find('span', class_='job-search-card__location')
                    link_tag = job_html.find('a', class_='base-card__full-link')
                    date_tag = job_html.find('time')

                    title = title_tag.text.strip() if title_tag else 'N/D'
                    company = company_tag.text.strip() if company_tag else 'N/D'
                    job_location = location_tag.text.strip() if location_tag else 'N/D'
                    job_url = link_tag['href'] if (link_tag and 'href' in link_tag.attrs) else 'N/D'
                    posted_date = date_tag.get('datetime') if date_tag else 'N/D'

                    if title != 'N/D' and job_url != 'N/D' and job_url not in seen_urls:
                        all_jobs.append({
                            'title': title,
                            'company': company,
                            'location': job_location,
                            'url': job_url,
                            'posted_date': posted_date
                        })
                        seen_urls.add(job_url)

                start_offset += 10
            except requests.RequestException as e:
                print(f"❌ Request failed: {e}", file=sys.stderr)
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}", file=sys.stderr)
                break

        return all_jobs[:max_results]
