import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import csv
import random
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import schedule
import time
from config import hotel_names, location

# SMTP2GO email configuration
SMTP_SERVER = "mail.smtp2go.com"
SMTP_PORT = 2525 #Example port
EMAIL_ADDRESS = "your_email"
EMAIL_PASSWORD = "your_password"

# User-Agent pool
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/116.0.1938.69 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
]

# Send email with an attachment
def send_email_with_attachment(subject, body, recipient, attachment, retries=3, delay=15):
    """
    Sends an email with a retry mechanism.

    Args:
        subject (str): The email subject.
        body (str): The email body.
        recipient (list or str): List of recipient email addresses or a single email address.
        attachment (str): Path to the file to be attached.
        retries (int): Number of retry attempts.
        delay (int): Delay in seconds between retries.
    """
    if isinstance(recipient, str):
        recipient = [recipient]  # Convert a single recipient to a list

    attempt = 0
    while attempt < retries:
        try:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_ADDRESS
            msg["To"] = ", ".join(recipient)
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            if os.path.exists(attachment):
                with open(attachment, "rb") as file:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(file.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(attachment)}",
                    )
                    msg.attach(part)

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, recipient, msg.as_string())  # Pass joined string here
            print(f"Email sent successfully with attachment: {attachment}")
            return
        except Exception as e:
            print(f"Error sending email: {e}")
            attempt += 1
            if attempt < retries:
                print(f"Retrying in {delay} seconds... (Attempt {attempt + 1}/{retries})")
                time.sleep(delay)
            else:
                print("Failed to send email after multiple attempts.")
# Scrape hotel prices
def scrape_hotel_prices(driver, hotel_name, checkin_dates):
    prices = []
    base_url = f"https://www.booking.com/hotel/pl/{location}/{hotel_name}.pl.html"

    for date in checkin_dates:
        checkin_date = datetime.strptime(date, "%Y-%m-%d")
        checkout_date = checkin_date + timedelta(days=1)
        params = (
            f"?checkin={checkin_date.strftime('%Y-%m-%d')}"
            f"&checkout={checkout_date.strftime('%Y-%m-%d')}"
            f"&group_adults=2&no_rooms=1&group_children=0"
            f"&aid=304142&lang=pl-PL"
            f"&selected_currency=PLN"
        )
        full_url = base_url + params
        print(f"Scraping URL for {hotel_name} on {date}: {full_url}")

        retries = 3  # Number of retries if the currency is not PLN
        for attempt in range(retries):
            try:
                driver.get(full_url)
                time.sleep(random.uniform(6, 13))

                try:
                    # Locate the first row of the table containing room information
                    first_row = driver.find_element(By.CSS_SELECTOR, 'tr.hprt-table-cheapest-block-fix')

                    # Try to locate the original price element within the first row
                    original_price_element = first_row.find_element(By.CSS_SELECTOR, 'div.bui-f-color-destructive.js-strikethrough-price.prco-inline-block-maker-helper.bui-price-display__original')
                    found_price = original_price_element.text

                    # Check if the price is in PLN
                    if "zł" in found_price:
                        print(f"Original price in PLN found for {hotel_name} on {date}: {found_price}")
                        prices.append((date, found_price))
                        break
                    else:
                        print(f"Price not in PLN for {hotel_name} on {date}: {found_price}")
                        if attempt < retries - 1:
                            print("Retrying...")
                            time.sleep(random.uniform(4, 11))
                        else:
                            print(f"Failed to get PLN price after {retries} attempts for {date}")
                            prices.append((date, "Not Available"))
                except NoSuchElementException:
                    # Fallback to the primary price element
                    price_element = driver.find_element(By.CSS_SELECTOR, 'span.prco-valign-middle-helper')
                    found_price = price_element.text if price_element else "Not Available"

                    # Check if the price is in PLN
                    if "zł" in found_price:
                        print(f"Fallback price in PLN found for {hotel_name} on {date}: {found_price}")
                        prices.append((date, found_price))
                        break
                    else:
                        print(f"Fallback price not in PLN for {hotel_name} on {date}: {found_price}")
                        if attempt < retries - 1:
                            print("Retrying...")
                            time.sleep(random.uniform(4, 11))
                        else:
                            print(f"Failed to get PLN price after {retries} attempts for {date}")
                            prices.append((date, "Not Available"))
            except (NoSuchElementException, TimeoutException, WebDriverException) as e:
                print(f"Error scraping data for {hotel_name} on {date}: {e}")
                if attempt < retries - 1:
                    print("Retrying...")
                    time.sleep(random.uniform(4, 11))
                else:
                    print(f"Failed to scrape data after {retries} attempts for {date}")
                    prices.append((date, "Not Available"))

    return prices

# Scrape booking prices
def scrape_booking_prices_selenium():
    checkin_dates = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(45)]

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument('--disable-gpu')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        for hotel_name in hotel_names:
            prices = scrape_hotel_prices(driver, hotel_name, checkin_dates)

            csv_filename = f"{hotel_name}_{datetime.now().strftime('%Y-%m-%d')}.csv"
            with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["Hotel Name", "Date", "Price"])
                for date, price in prices:
                    writer.writerow([hotel_name, date, price])

            print(f"Data saved to {csv_filename}")

            subject = f"Scraping Results for {hotel_name}_{datetime.now().strftime('%Y-%m-%d')}"
            body = f"The scraping results for {hotel_name}_{datetime.now().strftime('%Y-%m-%d')} are attached."
            recipient = ["recipient_email1", "recipient_email2"]
            send_email_with_attachment(subject, body, recipient, csv_filename)

    finally:
        driver.quit()

# Job to run daily
def daily_job():
    print("Starting daily scraping job...")
    scrape_booking_prices_selenium()

# Schedule the job
schedule.every().day.at("00:40").do(daily_job)

if __name__ == "__main__":
    print("Scheduler is running. Waiting for the next job...")
    while True:
        schedule.run_pending()
        time.sleep(1)