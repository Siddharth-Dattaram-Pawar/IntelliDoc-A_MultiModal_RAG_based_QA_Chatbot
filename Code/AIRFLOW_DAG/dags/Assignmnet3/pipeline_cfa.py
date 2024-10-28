import os 
import logging
import requests
import boto3
import pandas as pd
from sqlalchemy import create_engine
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from airflow import DAG
from airflow.operators.python import PythonOperator
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime
import time
import snowflake.connector
import random
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://rpc.cfainstitute.org"

class CFAInstituteScraper:
    def __init__(self) -> None:
        self.driver = None
        self.titles = []
        self.summaries = []
        self.image_links = []
        self.pdf_links = []
        self.publication_links = []
        self.processed_items = set()

    def setup_driver(self) -> None:
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_service = Service(executable_path="/usr/local/bin/chromedriver")
            self.driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
            logger.info("Web driver setup successfully.")
        except Exception as e:
            logger.error(f"Failed to set up the web driver: {e}")
            raise

    def start_scraping(self) -> None:
        try:
            self.driver.get(f'{BASE_URL}/en/research-foundation/publications#sort=%40officialz32xdate%20descending&f:SeriesContent=[Research%20Foundation]')
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".coveo-result-frame")))
            logger.info("Navigated to the CFA Institute publications page.")
            self.dismiss_privacy_banner()
            self.scrape_all_pages()
        except Exception as e:
            logger.error(f"Failed to start scraping: {e}")
            raise

    def dismiss_privacy_banner(self) -> None:
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "privacy-banner"))
            )
            self.driver.execute_script("""
                let banner = document.getElementById('privacy-banner');
                if (banner) {
                    let closeButton = banner.querySelector('.alert-dismissable');
                    if (closeButton) closeButton.click();
                }
            """)
            logger.info("Privacy banner dismissed successfully.")
        except TimeoutException:
            logger.info("Privacy banner was not present, proceeding.")
        except Exception as e:
            logger.error(f"Error dismissing privacy banner: {e}")

    def scroll_to_bottom(self) -> None:
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1, 3))  # Random wait between 1 and 3 seconds
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def scrape_all_pages(self) -> None:
        page_number = 1
        while True:
            logger.info(f"Scraping page {page_number}")
            self.scroll_to_bottom()
            self.scrape_publication_list()
            try:
                next_button = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".coveo-pager-next"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                logger.info("Navigating to the next page.")
                self.driver.execute_script("arguments[0].click();", next_button)
                WebDriverWait(self.driver, 20).until(
                    EC.staleness_of(next_button)
                )
                page_number += 1
                time.sleep(random.uniform(2, 5))  # Random wait between 2 and 5 seconds
            except (TimeoutException, StaleElementReferenceException) as e:
                logger.info(f"No more pages or failed to navigate: {e}")
                break


    def scrape_publication_list(self) -> None:
        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".coveo-result-frame")))
            publications = self.driver.find_elements(By.CSS_SELECTOR, ".coveo-result-frame")
            logger.info(f"Found {len(publications)} publications on this page.")

            for publication in publications:
                try:
                    title = self.get_element_text(publication.find_element(By.CSS_SELECTOR, "h4.coveo-title a"))
                    if title in self.processed_items:
                        logger.info(f"Skipping already processed item: {title}")
                        continue
                
                    self.processed_items.add(title)
                    # Try to get the image link, but use 'N/A' if not found
                    try:
                        image_element = publication.find_element(By.CSS_SELECTOR, "img.coveo-result-image")
                        image_link = self.get_element_attribute(image_element, 'src')
                        image_link = self.normalize_url(image_link)
                    except NoSuchElementException:
                        logger.info(f"No image found for publication: {title}")
                        image_link = 'N/A'

                    publication_link = self.get_element_attribute(publication.find_element(By.CSS_SELECTOR, "a.CoveoResultLink"), 'href')
                    publication_link = self.normalize_url(publication_link)
                    summary = self.extract_summary(publication)

                    self.titles.append(title)
                    self.image_links.append(image_link)
                    self.publication_links.append(publication_link)
                    self.summaries.append(summary)

                    logger.info(f"Processed: {title}")

                except Exception as e:
                    logger.error(f"Failed to process a publication: {e}")
                    continue  # Continue with the next publication even if this one fails

        except Exception as e:
            logger.error(f"Failed to scrape publication list: {e}")

    def get_element_text(self, element) -> str:
        return WebDriverWait(self.driver, 10).until(EC.visibility_of(element)).text.strip()

    def get_element_attribute(self, element, attribute: str) -> str:
        return WebDriverWait(self.driver, 10).until(EC.visibility_of(element)).get_attribute(attribute)

    def normalize_url(self, url: str) -> str:
        if url.startswith('//'):
            return f"https:{url}"
        elif url.startswith('/'):
            return f"{BASE_URL}{url}"
        elif not url.startswith(('http://', 'https://')):
            return f"{BASE_URL}/{url}"
        return url

    def extract_summary(self, publication) -> str:
        try:
            summary = self.get_element_text(publication.find_element(By.CSS_SELECTOR, "div.result-body"))
            return summary if summary else 'N/A'
        except Exception as e:
            logger.info(f"Summary not found: {e}")
            return 'N/A'

    def extract_pdf_links(self) -> None:
        for link in self.publication_links:
            if link != 'N/A':
                try:
                    self.driver.get(link)
                    pdf_link = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href$=".pdf"]'))
                    ).get_attribute('href')
                    pdf_link = self.normalize_url(pdf_link)
                    self.pdf_links.append(pdf_link)
                    logger.info(f"PDF Link: {pdf_link}")
                    time.sleep(random.uniform(1, 3))  # Random wait between 1 and 3 seconds
                except Exception as e:
                    logger.error(f"Failed to extract PDF link for {link}: {e}")
                    self.pdf_links.append('N/A')
            else:
                self.pdf_links.append('N/A')

    def close_driver(self) -> None:
        if self.driver:
            self.driver.quit()
            logger.info("Driver closed successfully.")

def upload_image_and_pdf_to_s3(bucket_name: str, image_links: List[str], pdf_links: List[str]) -> Tuple[List[str], List[str]]:
    s3_client = boto3.client('s3')
    s3_image_links, s3_pdf_links = [], []

    for link_list, prefix, link_type in [(image_links, 'images_new', 'image'), (pdf_links, 'pdfs_new', 'PDF')]:
        for link in link_list:
            if link != 'N/A':
                try:
                    file_name = os.path.basename(link.split("?")[0])
                    s3_key = f'{prefix}/{file_name}'
                    
                    if not object_exists_in_s3(s3_client, bucket_name, s3_key):
                        response = requests.get(link, stream=True)
                        if response.status_code == 200:
                            s3_client.upload_fileobj(response.raw, bucket_name, s3_key)
                            logger.info(f"Uploaded {link_type} {file_name} to S3.")
                        else:
                            logger.error(f"Failed to download {link_type} from {link}: {response.status_code}")
                            (s3_image_links if link_type == 'image' else s3_pdf_links).append('N/A')
                            continue
                    else:
                        logger.info(f"{link_type} {file_name} already exists in S3. Skipping upload.")
                    
                    s3_link = f"s3://{bucket_name}/{s3_key}"
                    (s3_image_links if link_type == 'image' else s3_pdf_links).append(s3_link)
                except Exception as e:
                    logger.error(f"Failed to upload {link_type} {link} to S3: {e}")
                    (s3_image_links if link_type == 'image' else s3_pdf_links).append('N/A')
            else:
                (s3_image_links if link_type == 'image' else s3_pdf_links).append('N/A')

    return s3_image_links, s3_pdf_links

def object_exists_in_s3(s3_client, bucket: str, key: str) -> bool:
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            raise

def insert_into_snowflake(titles: List[str], summaries: List[str], s3_image_links: List[str], s3_pdf_links: List[str]) -> None:
    try:
        conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE'),
            schema=os.getenv('SNOWFLAKE_SCHEMA')
        )
        
        cursor = conn.cursor()
        
        for title, summary, s3_image_link, s3_pdf_link in zip(titles, summaries, s3_image_links, s3_pdf_links):
            try:
                cursor.execute("SELECT 1 FROM CFA_NEW WHERE title = %s", (title,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO CFA_NEW (title, summary, image_link, pdf_link) VALUES (%s, %s, %s, %s)",
                        (title, summary, s3_image_link, s3_pdf_link)
                    )
                    logger.info(f"Inserted '{title}' into Snowflake.")
                else:
                    logger.info(f"Title '{title}' already exists in Snowflake. Skipping insertion.")
            except Exception as e:
                logger.error(f"Failed to insert '{title}' into Snowflake: {e}")
                    
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to connect to Snowflake: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def initialize_scraper() -> Dict[str, object]:
    scraper = CFAInstituteScraper()
    scraper.setup_driver()
    return {
        'driver_initialized': True,
        'processed_items': list(scraper.processed_items)
    }

def scrape_publications(**context) -> Dict[str, List[str]]:
    ti = context['ti']
    setup_info = ti.xcom_pull(task_ids='setup_driver')
    
    scraper = CFAInstituteScraper()
    scraper.setup_driver()
    scraper.processed_items = set(setup_info['processed_items'])
    
    scraper.start_scraping()
    
    return {
        'titles': scraper.titles,
        'summaries': scraper.summaries,
        'image_links': scraper.image_links,
        'publication_links': scraper.publication_links,
        'processed_items': list(scraper.processed_items)
    }

def extract_pdfs(**context) -> Dict[str, List[str]]:
    ti = context['ti']
    scrape_info = ti.xcom_pull(task_ids='scrape_publications')
    
    scraper = CFAInstituteScraper()
    scraper.setup_driver()
    scraper.publication_links = scrape_info['publication_links']
    
    scraper.extract_pdf_links()
    
    return {
        'pdf_links': scraper.pdf_links
    }

def upload_to_s3(**context) -> Dict[str, List[str]]:
    ti = context['ti']
    scrape_info = ti.xcom_pull(task_ids='scrape_publications')
    pdf_info = ti.xcom_pull(task_ids='extract_pdfs')
    
    bucket_name = os.getenv('AWS_BUCKET')
    s3_image_links, s3_pdf_links = upload_image_and_pdf_to_s3(bucket_name, scrape_info['image_links'], pdf_info['pdf_links'])
    
    return {
        's3_image_links': s3_image_links,
        's3_pdf_links': s3_pdf_links
    }

def insert_data(**context) -> None:
    ti = context['ti']
    scrape_info = ti.xcom_pull(task_ids='scrape_publications')
    s3_info = ti.xcom_pull(task_ids='upload_to_s3')
    
    insert_into_snowflake(scrape_info['titles'], scrape_info['summaries'], s3_info['s3_image_links'], s3_info['s3_pdf_links'])

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

with DAG('cfa_institute_scraper_dag_new', default_args=default_args, schedule_interval='@daily', catchup=False) as dag:
    
    setup_task = PythonOperator(
        task_id='setup_driver',
        python_callable=initialize_scraper,
        provide_context=True
    )

    scrape_task = PythonOperator(
        task_id='scrape_publications',
        python_callable=scrape_publications,
        provide_context=True
    )

    extract_task = PythonOperator(
        task_id='extract_pdfs',
        python_callable=extract_pdfs,
        provide_context=True
    )

    upload_task = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_to_s3,
        provide_context=True
    )

    insert_task = PythonOperator(
        task_id='insert_data',
        python_callable=insert_data,
        provide_context=True
    )

    setup_task >> scrape_task >> extract_task >> upload_task >> insert_task
