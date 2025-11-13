from bs4 import BeautifulSoup
import selenium 
import csv
import time
import re
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains 

class FlipkartScapper:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def get_top_reviews(self, product_url, counts = 5):
        pass
    
    def scrape_flipkart_products(self, query, max_products = 4, review_counts = 4):
        pass

    def save_to_csv(self, data, filename = "scraped_data.csv"):
        pass

    