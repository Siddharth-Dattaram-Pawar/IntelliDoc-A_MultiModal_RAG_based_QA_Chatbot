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
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class CFAInstituteScraper:
    def __init__(self):
        self.driver = None
        self.titles = []
        self.summaries = []
        self.image_links = []
        self.pdf_links = []
        self.publication_links = []

    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")  # To handle resource constraints in containerized environments
            #chrome_service = Service(executable_path=ChromeDriverManager().install())
            chrome_service = Service(executable_path="/usr/local/bin/chromedriver")
            self.driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
            logging.debug("Web driver setup successfully.")
        except Exception as e:
            logging.error(f"Failed to set up the web driver: {e}")
            raise

    def start_scraping(self):
        try:
            self.driver.get('https://rpc.cfainstitute.org/en/research-foundation/publications#sort=%40officialz32xdate%20descending&f:SeriesContent=[Research%20Foundation]')
            logging.debug("Navigated to the CFA Institute publications page.")
            self.dismiss_privacy_banner()
            self.scrape_all_pages()
        except Exception as e:
            logging.error(f"Failed to start scraping: {e}")
            raise

    def dismiss_privacy_banner(self):
        try:
            privacy_banner = self.driver.find_element(By.ID, "privacy-banner")
            dismiss_button = privacy_banner.find_element(By.CLASS_NAME, "alert-dismissable")
            dismiss_button.click()
            logging.debug("Privacy banner dismissed successfully.")
        except Exception as e:
            logging.debug(f"Privacy banner not found or could not be dismissed: {e}")

    def scrape_all_pages(self):
        while True:
            self.scrape_publication_list()
            try:
                self.dismiss_privacy_banner()
                next_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".coveo-pager-next"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                logging.debug("Navigating to the next page.")
                next_button.click()

                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".coveo-result-frame"))
                )
            except Exception as e:
                logging.debug(f"No more pages or failed to navigate: {e}")
                break

    def scrape_publication_list(self):
        try:
            publications = self.driver.find_elements(By.CSS_SELECTOR, ".coveo-result-frame")
            logging.debug(f"Found {len(publications)} publications on this page.")

            for publication in publications:
                try:
                    title_element = publication.find_element(By.CSS_SELECTOR, "h4.coveo-title a")
                    title = title_element.text
                except Exception as e:
                    title = 'N/A'
                    logging.debug(f"Title not found: {e}")

                logging.debug(f"Title: {title}")

                try:
                    image_element = publication.find_element(By.CSS_SELECTOR, "img.coveo-result-image")
                    image_link = image_element.get_attribute('src')
                except Exception as e:
                    image_link = 'N/A'
                    logging.debug(f"Image link not found: {e}")

                logging.debug(f"Image Link: {image_link}")

                try:
                    publication_link = publication.find_element(By.CSS_SELECTOR, "a.CoveoResultLink").get_attribute('href')
                except Exception as e:
                    publication_link = 'N/A'
                    logging.debug(f"Publication link not found: {e}")

                logging.debug(f"Publication Link: {publication_link}")

                self.titles.append(title)
                self.image_links.append(image_link)
                self.publication_links.append(publication_link)

                summary = self.extract_summary(publication)
                self.summaries.append(summary)

        except Exception as e:
            logging.error(f"Failed to scrape publication list: {e}")

    def extract_summary(self, publication):
        try:
            summary_element = publication.find_element(By.CSS_SELECTOR, "div.result-body")
            summary = summary_element.text
            if summary.strip() == '':
                summary = 'N/A'
            logging.debug(f"Summary: {summary}")
        except Exception as e:
            summary = 'N/A'
            logging.debug(f"Summary not found: {e}")
        return summary

    def extract_pdf_links(self):
        for link in self.publication_links:
            try:
                if link != 'N/A':
                    # Open the publication link in the same tab (instead of opening a new one)
                    self.driver.get(link)
                
                    # Wait for the PDF link to become available
                    pdf_link_element = WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href$=".pdf"]'))
                    )
                    pdf_link = pdf_link_element.get_attribute('href')
                    logging.debug(f"PDF Link: {pdf_link}")

                    # Store the PDF link
                    self.pdf_links.append(pdf_link)
                else:
                    self.pdf_links.append('N/A')

            except Exception as e:
                logging.error(f"Failed to extract PDF link for {link}: {e}")
                self.pdf_links.append('N/A')

                # Reinitialize the session in case of failure
                self.restart_driver()

    def close_driver(self):
        try:
            if self.driver:
                self.driver.quit()
                logging.debug("Driver closed successfully.")
        except Exception as e:
            logging.error(f"Failed to close the driver: {e}")

def restart_driver_on_failure(scraper):
    """
    Helper function to restart the driver if it crashes.
    """
    logging.debug("Restarting the driver due to failure.")
    scraper.close_driver()
    time.sleep(5)  # Sleep before reinitializing to avoid immediate crash loop
    scraper.setup_driver()

def upload_image_and_pdf_to_s3(bucket_name, image_links, pdf_links):
    s3_client = boto3.client('s3')

    for image_link in image_links:
        try:
            if image_link != 'N/A':
                response = requests.get(image_link, stream=True)
                if response.status_code == 200:
                    s3_client.upload_fileobj(response.raw, bucket_name, f'images/{os.path.basename(image_link)}')
                    logging.debug(f"Uploaded image from {image_link} to S3.")
                else:
                    logging.error(f"Failed to download image from {image_link}: {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to upload image {image_link} to S3: {e}")

    for pdf_link in pdf_links:
        try:
            if pdf_link != 'N/A':
                response = requests.get(pdf_link, stream=True)
                if response.status_code == 200:
                    s3_client.upload_fileobj(response.raw, bucket_name, f'pdfs/{os.path.basename(pdf_link)}')
                    logging.debug(f"Uploaded PDF from {pdf_link} to S3.")
                else:
                    logging.error(f"Failed to download PDF from {pdf_link}: {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to upload PDF {pdf_link} to S3: {e}")

def insert_into_snowflake(titles, summaries, image_links, pdf_links):
    try:
        conn = create_engine(os.getenv('SNOWFLAKE_CONNECTION'))
        with conn.connect() as connection:
            for title, summary, image_link, pdf_link in zip(titles, summaries, image_links, pdf_links):
                if image_link != 'N/A' and pdf_link != 'N/A':
                    try:
                        connection.execute(
                            f"""
                            INSERT INTO CFA (title, summary, image_link, pdf_link)
                            SELECT '{title}', '{summary}', '{image_link}', '{pdf_link}'
                            WHERE NOT EXISTS (
                                SELECT 1 FROM CFA WHERE title = '{title}'
                            )
                            """
                        )
                        logging.debug(f"Inserted {title} into Snowflake.")
                    except Exception as e:
                        logging.error(f"Failed to insert {title} into Snowflake: {e}")
    except Exception as e:
        logging.error(f"Failed to connect to Snowflake: {e}")


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
}

def scrape_and_process():
    scraper = CFAInstituteScraper()
    try:
        # Scraper setup
        scraper.setup_driver()
        
        # Start scraping
        scraper.start_scraping()

        # Extract PDF links
        scraper.extract_pdf_links()

        # Upload to S3
        bucket_name = os.getenv('AWS_BUCKET')
        upload_image_and_pdf_to_s3(bucket_name, scraper.image_links, scraper.pdf_links)

        # Insert data into Snowflake
        insert_into_snowflake(scraper.titles, scraper.summaries, scraper.image_links, scraper.pdf_links)

    except Exception as e:
        logging.error(f"An error occurred during the scrape and process workflow: {e}")
        restart_driver_on_failure(scraper)
    finally:
        # Always ensure the driver is closed
        scraper.close_driver()


# Define Airflow DAG
with DAG('cfa_institute_scraper_dag', default_args=default_args, schedule_interval='@daily') as dag:
    scrape_task = PythonOperator(
        task_id='scrape_and_process',
        python_callable=scrape_and_process,
    )
