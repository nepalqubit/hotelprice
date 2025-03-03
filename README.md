A Python script that automates the process of scraping hotel prices from Booking.com and sending the results via email as CSV attachments. The script uses Selenium for web scraping and Schedule for daily automation.

Features
Automated Scraping: Retrieves hotel prices for a range of check-in dates (up to 45 days ahead) from Booking.com.
CSV Reporting: Saves scraped data into CSV files for each hotel.
Email Notifications: Sends out the CSV reports as email attachments using SMTP2GO.
Daily Scheduler: Automatically runs the scraping job every day at a specified time (default is 00:40).
Prerequisites
Python 3.6+
Google Chrome Browser installed on your system.
ChromeDriver: Managed automatically by webdriver_manager.
