import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

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
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    def start_scraping(self):
        self.driver.get('https://rpc.cfainstitute.org/en/research-foundation/publications#sort=%40officialz32xdate%20descending&f:SeriesContent=[Research%20Foundation]')
        self.dismiss_privacy_banner()
        time.sleep(5)  # Wait for the page to load fully
        self.scrape_all_pages()

    def dismiss_privacy_banner(self):
        try:
            # Attempt to dismiss privacy banner
            privacy_banner = self.driver.find_element(By.ID, "privacy-banner")
            dismiss_button = privacy_banner.find_element(By.CLASS_NAME, "alert-dismissable")
            dismiss_button.click()
            logging.debug("Privacy banner dismissed successfully.")
        except Exception as e:
            logging.debug(f"Privacy banner not found or could not be dismissed: {e}")
    
    def scrape_all_pages(self):
        """Scrape all the pages by navigating through pagination."""
        while True:
            # Scrape publications on the current page
            self.scrape_publication_list()
        
            # Try to click the "Next" button to go to the next page
            try:
                self.dismiss_privacy_banner()

                # Scroll the "Next" button into view before clicking
                next_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".coveo-pager-next"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                logging.debug("Navigating to the next page.")
                next_button.click()

                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".coveo-result-frame"))
                )
                time.sleep(3)  # Give some extra time for the page to load completely
            
            except Exception as e:
                logging.debug(f"No more pages or failed to navigate: {e}")
                break

    def scrape_publication_list(self):
        try:
            publications = self.driver.find_elements(By.CSS_SELECTOR, ".coveo-result-frame")
            logging.debug(f"Found {len(publications)} publications on this page.")

            for publication in publications:
                # Extract title
                try:
                    title_element = publication.find_element(By.CSS_SELECTOR, "h4.coveo-title a")
                    title = title_element.text
                except Exception as e:
                    title = 'N/A'
                    logging.debug(f"Title not found: {e}")
                logging.debug(f"Title: {title}")

                # Extract image link
                try:
                    image_element = publication.find_element(By.CSS_SELECTOR, "img.coveo-result-image")
                    image_link = image_element.get_attribute('src')
                except Exception as e:
                    image_link = 'N/A'
                    logging.debug(f"Image link not found: {e}")
                logging.debug(f"Image Link: {image_link}")

                # Extract publication link (to open later for the PDF link)
                try:
                    publication_link = publication.find_element(By.CSS_SELECTOR, "a.CoveoResultLink").get_attribute('href')
                except Exception as e:
                    publication_link = 'N/A'
                    logging.debug(f"Publication link not found: {e}")
                logging.debug(f"Publication Link: {publication_link}")

                # Add title, image link, and publication link to lists
                self.titles.append(title)
                self.image_links.append(image_link)
                self.publication_links.append(publication_link)

                # For summary extraction (located in `result-body`)
                summary = self.extract_summary(publication)
                self.summaries.append(summary)

            # Now extract the PDF links by visiting each publication link
            self.extract_pdf_links()

        except Exception as e:
            logging.error(f"Failed to scrape publication list: {e}")

    def extract_summary(self, publication):
        """Extract the 2-line summary for each publication (if available)."""
        try:
            summary_element = publication.find_element(By.CSS_SELECTOR, "div.result-body")
            summary = summary_element.text
            if summary.strip() == '':
                summary = 'N/A'  # Handle cases where summary is present but empty
            logging.debug(f"Summary: {summary}")
        except Exception as e:
            summary = 'N/A'  # Placeholder in case summary is not found
            logging.debug(f"Summary not found: {e}")
        return summary

    def extract_pdf_links(self):
        """Open each publication link and extract the PDF link."""
        for link in self.publication_links:
            try:
                if link != 'N/A':  # Skip 'N/A' links
                    self.driver.execute_script(f"window.open('{link}', '_blank');")
                    self.driver.switch_to.window(self.driver.window_handles[-1])

                    # Wait for publication page to load and locate PDF link
                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href$=".pdf"]')))
                    pdf_link = self.driver.find_element(By.CSS_SELECTOR, 'a[href$=".pdf"]').get_attribute('href')
                    logging.debug(f"PDF Link: {pdf_link}")

                    self.pdf_links.append(pdf_link)

                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                else:
                    self.pdf_links.append('N/A')

            except Exception as e:
                logging.error(f"Failed to extract PDF link for {link}: {e}")
                self.pdf_links.append('N/A')  # In case no PDF link is found

    def save_to_csv(self):
        try:
            # Ensure all lists have the same length
            min_length = min(len(self.titles), len(self.summaries), len(self.image_links), len(self.pdf_links))
            self.titles = self.titles[:min_length]
            self.summaries = self.summaries[:min_length]
            self.image_links = self.image_links[:min_length]
            self.pdf_links = self.pdf_links[:min_length]

            # Create a DataFrame with the collected data
            df = pd.DataFrame({
                'Title': self.titles,
                'Summary': self.summaries,
                'Image Link': self.image_links,
                'PDF Link': self.pdf_links
            })
            logging.debug("DataFrame created successfully.")
            
            # Save the DataFrame to a CSV file
            df.to_csv('cfa_publications.csv', index=False)
            logging.debug("Data saved to cfa_publications.csv")
        
        except Exception as e:
            logging.error(f"Failed to create DataFrame or save CSV: {e}")

    def close_driver(self):
        if self.driver:
            self.driver.quit()


if __name__ == "__main__":
    scraper = CFAInstituteScraper()
    scraper.setup_driver()
    scraper.start_scraping()
    scraper.save_to_csv()
    scraper.close_driver()
