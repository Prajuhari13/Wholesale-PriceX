"""
Streamlit Web Scraper for Fruits & Vegetables Prices
====================================================

LEGAL & ETHICAL NOTICE:
- Always check robots.txt and Terms of Service before scraping
- Use for personal/research purposes only
- Respect rate limits and avoid overloading servers

Dependencies (see requirements.txt):
streamlit>=1.28.0
selenium>=4.15.0
beautifulsoup4>=4.12.0
pandas>=2.0.0
webdriver-manager>=4.0.0
openpyxl>=3.1.0
"""

import streamlit as st
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
from datetime import datetime
import io
import random


class PriceScraper:
    """Base scraper class with common functionality"""
    
    def __init__(self, headless=True):
        self.driver = self._init_driver(headless)
        
    def _init_driver(self, headless):
        """Initialize Selenium WebDriver with Chrome"""
        options = Options()
        if headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
    
    def random_delay(self, min_sec=2, max_sec=4):
        """Add random delay to avoid detection"""
        time.sleep(random.uniform(min_sec, max_sec))


class HyperpureScraper(PriceScraper):
    """Scraper for Hyperpure wholesale prices"""
    
    FRUITS_VEG_URL = "https://www.hyperpure.com/in/fruits-vegetables"
    
    def scrape(self, progress_callback=None):
        """Main scraping method for Hyperpure - scrapes from fruits-vegetables page"""
        if progress_callback:
            progress_callback("🔍 Starting Hyperpure scraper...")
        
        all_items = []
        
        try:
            # Navigate to fruits and vegetables page
            if progress_callback:
                progress_callback("📱 Loading Hyperpure Fruits & Vegetables page...")
            
            self.driver.get(self.FRUITS_VEG_URL)
            self.random_delay(6, 8) # Increased wait time
            
            # Handle popups
            if progress_callback:
                progress_callback("🔧 Handling popups and location selection...")
            self._handle_popups()
            self.random_delay(3, 4)
            
            # Try clicking on "All" filter to ensure all items are shown
            try:
                all_button = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'All')]")
                if all_button:
                    all_button[0].click()
                    time.sleep(3)
            except:
                pass
            
            # Scroll to load all products - MUCH MORE AGGRESSIVE
            if progress_callback:
                progress_callback("📜 Scrolling to load ALL products (this may take 2-3 minutes)...")
            self._scroll_page()
            
            # Additional wait to ensure all content is loaded
            time.sleep(5)
            
            # Scrape products
            if progress_callback:
                progress_callback("🔎 Extracting product data...")
            all_items = self._scrape_all_products()
            
            if progress_callback:
                progress_callback(f"✅ Found {len(all_items)} items from Hyperpure")
            
            # If we still have very few items, try alternative method
            if len(all_items) < 10:
                if progress_callback:
                    progress_callback("🔄 Trying alternative extraction method...")
                
                # Save page source for debugging
                with open('hyperpure_debug.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                
                if progress_callback:
                    progress_callback("⚠️ Few items found. Page source saved to hyperpure_debug.html for inspection.")
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Error scraping Hyperpure: {str(e)}")
        
        return self._create_dataframe(all_items, "Hyperpure")
    
    def _handle_popups(self):
        """Handle any popups or modals"""
        try:
            time.sleep(2)
            close_selectors = [
                'button[aria-label*="close"]',
                'button[class*="close"]',
                '.close-button',
                '[data-testid*="close"]',
                'button:has(svg)',
                '.modal-close',
                '[class*="close"]'
            ]
            
            for selector in close_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            elem.click()
                            time.sleep(1)
                            return
                except:
                    continue
        except:
            pass
    
    def _scroll_page(self):
        """Scroll page to load all dynamic content - SUPER AGGRESSIVE"""
        try:
            # First, wait for initial content to load
            time.sleep(4)
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_pause = 3 # Increased pause time
            no_change_count = 0
            max_no_change = 5 # Allow more attempts
            
            for scroll_attempt in range(50): # Increased to 50 attempts
                # Scroll to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause)
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    no_change_count += 1
                    if no_change_count >= max_no_change:
                        # Final attempts - scroll up and down multiple times
                        for _ in range(3):
                            self.driver.execute_script("window.scrollTo(0, 0);")
                            time.sleep(2)
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(3)
                        break
                else:
                    no_change_count = 0
                    
                last_height = new_height
                
                # Progressive scrolling - scroll in smaller increments every few attempts
                if scroll_attempt % 3 == 0:
                    for i in range(10):
                        scroll_position = (i + 1) * (new_height // 10)
                        self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                        time.sleep(0.8)
                        
        except Exception as e:
            pass
    
    def _scrape_all_products(self):
        """Scrape ALL products from current page - ENHANCED VERSION"""
        items = []
        try:
            # Wait for products to load
            time.sleep(4)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Try ALL possible selectors comprehensively
            all_selectors = [
                'div[class*="ProductCard"]',
                'div[class*="product-card"]',
                'div[class*="ProductTile"]',
                'div[class*="productCard"]',
                'div[class*="Card"]',
                'div[data-testid*="product"]',
                'article[class*="product"]',
                'article',
                'div[class*="card"]',
                'div[class*="item"]',
                '[data-qa*="product"]',
                '[class*="product-item"]'
            ]
            
            products = []
            # Try each selector and keep the best result
            for selector in all_selectors:
                found = soup.select(selector)
                if len(found) > len(products):
                    products = found
            
            print(f"Method 1: Found {len(products)} product elements")
            
            # Method 2: Find by structure - elements with both name and price
            if len(products) < 20:
                all_divs = soup.find_all(['div', 'article', 'section'])
                for div in all_divs:
                    text = div.get_text()
                    # Must have price and reasonable length
                    if re.search(r'₹\s*\d+', text) and 20 < len(text) < 600:
                        # Check if not already in products
                        if div not in products:
                            products.append(div)
                
                print(f"Method 2: Total {len(products)} product elements")
            
            # Method 3: Find by price elements and traverse up
            if len(products) < 20:
                price_elements = soup.find_all(string=re.compile(r'₹\s*\d+'))
                for price_elem in price_elements:
                    parent = price_elem.find_parent()
                    # Go up 3-7 levels to find the product card
                    for level in range(3, 8):
                        if parent:
                            parent_text = parent.get_text()
                            if (20 < len(parent_text) < 600 and
                                re.search(r'₹\s*\d+', parent_text)):
                                if parent not in products:
                                    products.append(parent)
                                    break
                            parent = parent.find_parent()
                
                print(f"Method 3: Total {len(products)} product elements")
            
            # Remove duplicates by comparing text content
            unique_products = []
            seen_texts = set()
            for product in products:
                text_signature = product.get_text()[:100] # First 100 chars
                if text_signature not in seen_texts:
                    seen_texts.add(text_signature)
                    unique_products.append(product)
            
            print(f"After deduplication: {len(unique_products)} unique products")
            
            # Extract information from all products
            seen_items = set()
            for product in unique_products:
                try:
                    item = self._extract_product_info(product)
                    if item:
                        # Create unique key
                        key = f"{item['name']}|{item['price']}"
                        if key not in seen_items:
                            seen_items.add(key)
                            items.append(item)
                except Exception as e:
                    continue
            
            print(f"Successfully extracted: {len(items)} items")
                    
        except Exception as e:
            print(f"Error in scrape_all_products: {e}")
        
        return items
    
    def _extract_product_info(self, element):
        """Extract name, price, and unit from product element - WITH BULK PRICING TIERS"""
        try:
            element_text = element.get_text()
            
            # Extract name - multiple strategies
            name = None
            
            # Strategy 1: Look for heading tags (most reliable)
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div']:
                name_elems = element.find_all(tag)
                for name_elem in name_elems:
                    text = name_elem.get_text(strip=True)
                    # Valid name: reasonable length, not a price, not just numbers
                    if (5 < len(text) < 100 and
                        not re.match(r'^₹', text) and
                        not re.match(r'^\d+\s*(kg|gm|pc)', text, re.I) and
                        not text.lower() in ['add', 'added', 'view', 'buy']):
                        # Check if it looks like a product name
                        if any(char.isalpha() for char in text):
                            name = text
                            break
                if name:
                    break
            
            # Strategy 2: Look for text before the price
            if not name:
                lines = [line.strip() for line in element_text.split('\n') if line.strip()]
                for i, line in enumerate(lines):
                    if re.search(r'₹\s*\d+', line):
                        # Name is likely in the previous lines
                        if i > 0:
                            for j in range(i-1, -1, -1):
                                potential_name = lines[j]
                                if (5 < len(potential_name) < 100 and
                                    not re.match(r'^\d+', potential_name) and
                                    any(char.isalpha() for char in potential_name)):
                                    name = potential_name
                                    break
                        if name:
                            break
            
            # Strategy 3: Find largest text block that's not a price or just a number
            if not name:
                all_text = element.find_all(string=True)
                candidates = []
                for text in all_text:
                    text = text.strip()
                    # Ensure it's not just a weight/quantity and has actual letters
                    if (10 < len(text) < 100 and
                        not re.search(r'₹\s*\d+', text) and
                        not re.match(r'^\d+(\.\d+)?\s*(kg|gm|g|pc|piece)', text, re.I) and
                        any(char.isalpha() for char in text)):
                        candidates.append(text)
                if candidates:
                    # Sort by length and take the longest one
                    candidates.sort(key=len, reverse=True)
                    name = candidates[0]
            
            # Strategy 4: If still no name, try to get the first meaningful text
            if not name:
                all_strings = [s.strip() for s in element.stripped_strings]
                for text in all_strings:
                    # Skip if it's just a quantity
                    if re.match(r'^\d+(\.\d+)?\s*(kg|gm|g|pc)', text, re.I):
                        continue
                    # Skip if it's a price
                    if re.match(r'^₹', text):
                        continue
                    # Take first meaningful text with letters
                    if len(text) > 4 and any(c.isalpha() for c in text):
                        name = text
                        break
            
            # Extract ALL prices and their corresponding units (bulk pricing tiers)
            # Look for patterns like "₹56/pc for 9 pcs+" or "₹57/pc for 5 pcs+"
            bulk_pricing_patterns = [
                r'₹\s*(\d+(?:\.\d+)?)\s*/\s*pc\s+for\s+(\d+)\s*pcs?\+', # per piece
                r'₹\s*(\d+(?:\.\d+)?)\s*/\s*kg\s+for\s+(\d+)\s*kgs?\+', # per kg
                r'₹\s*(\d+(?:\.\d+)?)\s*/\s*gm\s+for\s+(\d+)\s*gms?\+', # per gm
                r'₹\s*(\d+(?:\.\d+)?)\s*/\s*piece\s+for\s+(\d+)\s*pieces?\+', # per piece variant
            ]
            
            bulk_prices = []
            for pattern in bulk_pricing_patterns:
                found = re.findall(pattern, element_text, re.I)
                if found:
                    bulk_prices.extend(found)
            
            # Extract base unit (e.g., "5 kg" or "1 Piece" from title)
            base_unit = None
            base_unit_match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|gm|g|pc|piece|pieces)', name if name else '', re.I)
            if base_unit_match:
                base_unit = f"{base_unit_match.group(1)} {base_unit_match.group(2)}"
            
            # Extract base price as the LAST price occurrence in the text (assuming base is listed last)
            price_matches = list(re.finditer(r'₹\s*(\d+(?:\.\d+)?)', element_text, re.I))
            main_price = None
            main_unit_type = None
            if price_matches:
                # Take the last price match as base price
                last_match = price_matches[-1]
                main_price = last_match.group(1)
                
                # Try to extract unit type from context around the base price
                start = last_match.start()
                end = last_match.end()
                context = element_text[max(0, start-50):end+50]
                unit_match = re.search(r'/(kg|pc|gm|piece)', context, re.I)
                if unit_match:
                    main_unit_type = unit_match.group(1)
                else:
                    # Fallback unit detection
                    unit_patterns = [
                        r'/(kg|pc|gm|piece)',
                        r'\s(kg|pc|gm|piece)\s',
                    ]
                    for up in unit_patterns:
                        unit_match = re.search(up, context, re.I)
                        if unit_match:
                            main_unit_type = unit_match.group(1)
                            break
            
            # Construct pricing information
            pricing_info = []
            
            # Add bulk pricing tiers (sorted from best to worst deal - largest quantity first)
            if bulk_prices:
                # Sort by quantity (descending) to show best deals first
                bulk_prices_sorted = sorted(bulk_prices, key=lambda x: int(x[1]), reverse=True)
                
                for price, qty in bulk_prices_sorted:
                    # Determine unit type from pattern or context
                    if 'pc' in element_text.lower() or 'piece' in element_text.lower():
                        pricing_info.append(f"₹{price}/pc for {qty}pcs+")
                    elif 'kg' in element_text.lower():
                        pricing_info.append(f"₹{price}/kg for {qty}kg+")
                    else:
                        pricing_info.append(f"₹{price} for {qty}+")
            
            # ALWAYS add base price if found
            if main_price:
                if main_unit_type:
                    pricing_info.append(f"Base: ₹{main_price}/{main_unit_type}")
                else:
                    pricing_info.append(f"Base: ₹{main_price}")
            
            # Fallback: if no pricing found at all, search for any price
            if not pricing_info:
                all_prices_in_text = re.findall(r'₹\s*(\d+(?:\.\d+)?)', element_text)
                if all_prices_in_text:
                    # Take the first price found
                    pricing_info.append(f"₹{all_prices_in_text[0]}")
            
            # Extract unit/quantity if not found in bulk pricing
            unit = base_unit
            if not unit:
                unit_patterns = [
                    r'(\d+\s*(?:kg|kgs|kilogram))',
                    r'(\d+\s*(?:g|gm|gram|gms))',
                    r'(\d+\s*(?:pc|pcs|piece|pieces))',
                    r'(\d+\s*(?:ltr|litre|liter|ml))',
                    r'(per\s+(?:kg|pc|piece|unit))',
                    r'(\d+\s*(?:dozen))',
                    r'(\d+\.?\d*\s*(?:kg|gm|g|pc))',
                ]
                
                for pattern in unit_patterns:
                    match = re.search(pattern, element_text, re.I)
                    if match:
                        unit = match.group(1).strip()
                        break
            
            # Only return if we have both name and pricing
            if name and pricing_info:
                # Clean up name - remove price info, extra whitespace
                name = re.sub(r'₹.*', '', name).strip()
                name = re.sub(r'\s+', ' ', name)
                
                # Remove common noise words
                name = re.sub(r'\b(add|added|view|buy|select|choose)\b', '', name, flags=re.I).strip()
                
                # STRICT validation - reject invalid names
                # Reject if name is ONLY a quantity or pack (e.g., "0.50 kg", "2 kg", "1 pack")
                only_qty_pattern = r'^[\d\.\s]+(kg|gm|g|pc|piece|pieces|pack|packs)$'
                if re.match(only_qty_pattern, name, re.I):
                    return None
                
                # Reject if name starts with just a number and unit
                starts_qty_pattern = r'^\d+(\.\d+)?\s*(kg|gm|g|pc|pack)'
                if re.match(starts_qty_pattern, name, re.I):
                    return None
                
                # Reject if name is too short (less than 5 characters)
                if len(name) < 5:
                    return None
                
                # Reject if name is mostly numbers
                letter_count = sum(c.isalpha() for c in name)
                if letter_count < 3:
                    return None
                
                # Reject if name is just punctuation and spaces
                if not any(c.isalnum() for c in name):
                    return None
                
                # Additional check: reject if name is ONLY "pack" or numeric variations
                if re.match(r'^(pack|packs|\d+\s*pack)$', name, re.I):
                    return None
                
                return {
                    'name': name,
                    'price': ' | '.join(pricing_info),
                    'unit': unit or 'N/A'
                }
        except Exception as e:
            pass
        
        return None
    
    def _create_dataframe(self, items, source):
        """Convert items list to DataFrame"""
        if not items:
            return pd.DataFrame(columns=['Name', 'Price', 'Unit'])
        
        df = pd.DataFrame(items)
        df.rename(columns={'name': 'Name', 'price': 'Price', 'unit': 'Unit'}, inplace=True)
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['Name', 'Price'], keep='first')
        
        return df


class WholesaleMandiScraper(PriceScraper):
    """Scraper for Wholesale Mandi prices"""
    
    BASE_URL = "https://wholesalemandi.com/products"
    
    def scrape(self, progress_callback=None):
        """Main scraping method - scrapes ALL products with pagination"""
        if progress_callback:
            progress_callback("🔍 Starting Wholesale Mandi scraper...")
        
        all_items = []
        page = 1
        max_pages = 50
        
        try:
            while page <= max_pages:
                url = f"{self.BASE_URL}?page={page}"
                
                if progress_callback:
                    progress_callback(f"Scraping Wholesale Mandi page {page}...")
                
                try:
                    self.driver.get(url)
                    self.random_delay(3, 5)
                    
                    # Scroll to load content
                    self._scroll_page()
                    
                    items = self._scrape_page()
                    
                    if not items or len(items) == 0:
                        if progress_callback:
                            progress_callback(f"✓ Reached last page ({page-1})")
                        break
                    
                    all_items.extend(items)
                    
                    if progress_callback:
                        progress_callback(f"✓ Page {page}: Found {len(items)} items (Total: {len(all_items)})")
                    
                    if not self._has_next_page():
                        break
                    
                    page += 1
                    
                except Exception as e:
                    break
                
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Error: {str(e)}")
        
        return self._create_dataframe(all_items, "Wholesale Mandi")
    
    def _scroll_page(self):
        """Scroll to load all content"""
        try:
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
        except:
            pass
    
    def _scrape_page(self):
        """Scrape ALL items from current page"""
        items = []
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            selectors = [
                'div[class*="product"]',
                'div[class*="item"]',
                'article',
                'div[class*="card"]',
                '.product-card',
                '.item-card'
            ]
            
            products = []
            for selector in selectors:
                found = soup.select(selector)
                if len(found) > len(products):
                    products = found
            
            # Backup method
            if len(products) < 5:
                price_elements = soup.find_all(string=re.compile(r'₹|Rs\.?\s*\d+'))
                for price_elem in price_elements:
                    parent = price_elem.find_parent()
                    for _ in range(5):
                        if parent:
                            parent = parent.find_parent()
                            if parent and parent not in products:
                                products.append(parent)
                                break
            
            seen_items = set()
            for product in products:
                try:
                    item = self._extract_product_info(product)
                    if item:
                        key = f"{item['name']}|{item['price']}"
                        if key not in seen_items:
                            seen_items.add(key)
                            items.append(item)
                except:
                    continue
                    
        except Exception as e:
            pass
        
        return items
    
    def _extract_product_info(self, element):
        """Extract product information"""
        try:
            # Extract name
            name = None
            
            for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
                name_elem = element.find(tag)
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    if len(name) > 2:
                        break
            
            if not name:
                name_elem = element.find(class_=re.compile(r'(title|name)', re.I))
                if name_elem:
                    name = name_elem.get_text(strip=True)
            
            if not name:
                texts = [t.strip() for t in element.stripped_strings]
                for text in texts:
                    if 5 < len(text) < 100 and not re.match(r'^₹|^Rs', text):
                        name = text
                        break
            
            # Extract price
            price = None
            text_content = element.get_text()
            
            price_patterns = [
                r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)',
                r'Rs\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
                r'INR\s*(\d+(?:,\d+)*(?:\.\d+)?)'
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, text_content)
                if match:
                    price = f"₹{match.group(1)}"
                    break
            
            # Extract unit
            unit = None
            unit_patterns = [
                r'(\d+\s*(?:kg|kgs|kilogram))',
                r'(\d+\s*(?:g|gm|gram|gms))',
                r'(\d+\s*(?:pc|pcs|piece|pieces))',
                r'(\d+\s*(?:ltr|litre|ml))',
                r'(per\s+(?:kg|pc|piece|unit))',
                r'/\s*(kg|gm|pc|piece|unit)'
            ]
            
            for pattern in unit_patterns:
                match = re.search(pattern, text_content, re.I)
                if match:
                    unit = match.group(1).strip()
                    break
            
            if name and price:
                name = re.sub(r'₹.*|Rs\.?.*', '', name).strip()
                name = ' '.join(name.split())
                
                return {
                    'name': name,
                    'price': price,
                    'unit': unit or 'N/A'
                }
                
        except:
            pass
        
        return None
    
    def _has_next_page(self):
        """Check if next page exists"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            next_indicators = [
                soup.select_one('a[rel="next"]'),
                soup.select_one('.next'),
                soup.select_one('[class*="next-page"]')
            ]
            return any(indicator is not None for indicator in next_indicators)
        except:
            return False
    
    def _create_dataframe(self, items, source):
        """Convert items to DataFrame"""
        if not items:
            return pd.DataFrame(columns=['Name', 'Price', 'Unit'])
        
        df = pd.DataFrame(items)
        df.rename(columns={'name': 'Name', 'price': 'Price', 'unit': 'Unit'}, inplace=True)
        df = df.drop_duplicates(subset=['Name', 'Price'], keep='first')
        
        return df


def extract_base_item_name(item_name):
    """
    Extract base item name for smart grouping
    E.g., 'Cauliflower (Big)' -> 'Cauliflower'
          'Carrot Ooty' -> 'Carrot'
    """
    if not item_name or not isinstance(item_name, str):
        return "Ungrouped"
    
    # Convert to lowercase for matching
    name_lower = item_name.lower()
    
    # Comprehensive list of fruits and vegetables
    base_items = [
        # Vegetables
        'cauliflower', 'carrot', 'potato', 'tomato', 'onion', 'cabbage',
        'brinjal', 'eggplant', 'capsicum', 'bell pepper', 'cucumber',
        'bottle gourd', 'ridge gourd', 'bitter gourd', 'pumpkin', 'beans',
        'okra', 'ladyfinger', 'spinach', 'coriander', 'mint', 'curry leaves',
        'ginger', 'garlic', 'beetroot', 'radish', 'turnip', 'green chilli',
        'red chilli', 'drumstick', 'cluster beans', 'french beans',
        'peas', 'sweet corn', 'baby corn', 'mushroom', 'lettuce',
        'broccoli', 'zucchini', 'celery', 'leek', 'spring onion',
        'green onion', 'fenugreek', 'methi', 'palak', 'dhaniya',
        'pudina', 'bhindi', 'karela', 'lauki', 'tinda', 'parwal',
        'arbi', 'colocasia', 'yam', 'sweet potato', 'tapioca',
        
        # Fruits
        'apple', 'banana', 'orange', 'mango', 'grapes', 'watermelon',
        'papaya', 'pineapple', 'pomegranate', 'guava', 'lemon', 'lime',
        'kiwi', 'strawberry', 'blueberry', 'cherry', 'peach', 'plum',
        'apricot', 'pear', 'dragon fruit', 'passion fruit', 'avocado',
        'coconut', 'jackfruit', 'melon', 'muskmelon', 'cantaloupe',
        'litchi', 'lychee', 'custard apple', 'sapota', 'chikoo',
        'fig', 'date', 'raisin', 'blackberry', 'raspberry',
        'mosambi', 'sweet lime', 'grapefruit'
    ]
    
    # Find the base item in the name
    for base in base_items:
        if base in name_lower:
            return base.title()
    
    # If no match, try to extract first meaningful word
    # Remove common descriptors first
    descriptors = ['fresh', 'organic', 'premium', 'frozen', 'combo', 'pack', 'big', 'small', 'medium', 'large']
    words = item_name.split()
    
    for word in words:
        word_lower = word.lower().strip('(),')
        if word_lower not in descriptors and len(word_lower) > 3:
            return word.strip('(),').title()
    
    return "Ungrouped"


def create_grouped_comparison(hyperpure_df, mandi_df):
    """Create grouped comparison with all items displayed in groups"""
    
    # Add base item column to both dataframes
    hyperpure_df['BaseItem'] = hyperpure_df['Name'].apply(extract_base_item_name)
    mandi_df['BaseItem'] = mandi_df['Name'].apply(extract_base_item_name)
    
    # Get all unique base items from both sources
    all_bases = set(hyperpure_df['BaseItem'].unique()) | set(mandi_df['BaseItem'].unique())
    
    # Separate "Ungrouped" and sort the rest
    grouped_bases = sorted([b for b in all_bases if b != "Ungrouped"])
    ungrouped_bases = ["Ungrouped"] if "Ungrouped" in all_bases else []
    
    # Combined list: grouped items first, ungrouped last
    all_bases_sorted = grouped_bases + ungrouped_bases
    
    # Create rows for the table
    table_rows = []
    
    for base_item in all_bases_sorted:
        # Get items for this base from both sources
        hp_items = hyperpure_df[hyperpure_df['BaseItem'] == base_item]
        wm_items = mandi_df[mandi_df['BaseItem'] == base_item]
        
        # Add group header row
        table_rows.append({
            'Group': f"📦 {base_item}",
            'Hyperpure_Name': '',
            'Hyperpure_Price': '',
            'Hyperpure_Unit': '',
            'WholesaleMandi_Name': '',
            'WholesaleMandi_Price': '',
            'WholesaleMandi_Unit': '',
            'IsGroupHeader': True
        })
        
        # Get max rows needed for this group
        max_rows = max(len(hp_items), len(wm_items), 1)
        
        # Add item rows
        for i in range(max_rows):
            row = {
                'Group': '',
                'IsGroupHeader': False
            }
            
            # Hyperpure item
            if i < len(hp_items):
                hp_row = hp_items.iloc[i]
                row['Hyperpure_Name'] = hp_row['Name']
                row['Hyperpure_Price'] = hp_row['Price']
                row['Hyperpure_Unit'] = hp_row['Unit']
            else:
                row['Hyperpure_Name'] = ''
                row['Hyperpure_Price'] = ''
                row['Hyperpure_Unit'] = ''
            
            # Wholesale Mandi item
            if i < len(wm_items):
                wm_row = wm_items.iloc[i]
                row['WholesaleMandi_Name'] = wm_row['Name']
                row['WholesaleMandi_Price'] = wm_row['Price']
                row['WholesaleMandi_Unit'] = wm_row['Unit']
            else:
                row['WholesaleMandi_Name'] = ''
                row['WholesaleMandi_Price'] = ''
                row['WholesaleMandi_Unit'] = ''
            
            table_rows.append(row)
    
    result_df = pd.DataFrame(table_rows)
    return result_df


def create_download_link(df):
    """Create download data for CSV and Excel"""
    # CSV
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    
    # Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Price Comparison')
    excel_data = output.getvalue()
    
    return csv, excel_data


def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="Wholesale PriceX",
        page_icon="🥬",
        layout="wide"
    )
    
    # Custom CSS for better styling
    st.markdown("""
        <style>
        .comparison-container {
            display: flex;
            gap: 20px;
            margin: 10px 0;
        }
        .source-column {
            flex: 1;
            padding: 15px;
            border-radius: 10px;
            background-color: #f8f9fa;
        }
        .hyperpure-col {
            border-left: 4px solid #2ecc71;
        }
        .mandi-col {
            border-left: 4px solid #3498db;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.title("🥬Wholesale priceX🍎")
    st.markdown("**Compare prices side-by-side from Hyperpure and Wholesale Mandi**")
    st.markdown("---")
    
    # Info section
    with st.expander("ℹ️ About this tool"):
        st.info("""
        This tool scrapes wholesale prices from:
        - **Hyperpure** - https://www.hyperpure.com/in/fruits-vegetables
        - **Wholesale Mandi** - https://wholesalemandi.com/products
        
        **Features:**
        - ✅ Side-by-side comparison view
        - ✅ Export to CSV/Excel
        - ✅ Real-time scraping progress
        - ✅ Search and filter functionality
        """)
    
    # Sidebar controls
    st.sidebar.header("⚙️ Settings")
    scrape_hyperpure = st.sidebar.checkbox("Scrape Hyperpure", value=True)
    scrape_mandi = st.sidebar.checkbox("Scrape Wholesale Mandi", value=True)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 Instructions")
    st.sidebar.markdown("""
    1. Select sources to scrape
    2. Click 'Start Scraping'
    3. Wait for completion
    4. View side-by-side comparison
    5. Download the data
    """)
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        start_button = st.button("🚀 Start Scraping", type="primary", use_container_width=True)
    
    with col2:
        if 'comparison_data' in st.session_state:
            st.success("✅ Data Ready")
        else:
            st.info("⏳ Ready to scrape")
    
    # Progress area
    progress_container = st.container()
    
    # Results area
    results_container = st.container()
    
    if start_button:
        if not scrape_hyperpure and not scrape_mandi:
            st.error("⚠️ Please select at least one source to scrape!")
            return
        
        # Clear previous data
        for key in ['hyperpure_data', 'mandi_data', 'comparison_data']:
            if key in st.session_state:
                del st.session_state[key]
        
        hyperpure_df = pd.DataFrame(columns=['Name', 'Price', 'Unit'])
        mandi_df = pd.DataFrame(columns=['Name', 'Price', 'Unit'])
        
        with progress_container:
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            # Hyperpure scraping
            if scrape_hyperpure:
                scraper = None
                try:
                    scraper = HyperpureScraper(headless=True)
                    
                    def progress_callback(msg):
                        status_text.markdown(f"### {msg}")
                    
                    hyperpure_df = scraper.scrape(progress_callback)
                    st.session_state['hyperpure_data'] = hyperpure_df
                    progress_bar.progress(50)
                    status_text.markdown(f"### ✅ Hyperpure: {len(hyperpure_df)} items scraped")
                    
                except Exception as e:
                    status_text.markdown(f"### ❌ Hyperpure error: {str(e)}")
                finally:
                    if scraper:
                        scraper.close()
            
            # Wholesale Mandi scraping
            if scrape_mandi:
                scraper = None
                try:
                    scraper = WholesaleMandiScraper(headless=True)
                    
                    def progress_callback(msg):
                        status_text.markdown(f"### {msg}")
                    
                    mandi_df = scraper.scrape(progress_callback)
                    st.session_state['mandi_data'] = mandi_df
                    progress_bar.progress(100)
                    status_text.markdown(f"### ✅ Wholesale Mandi: {len(mandi_df)} items scraped")
                    
                except Exception as e:
                    status_text.markdown(f"### ❌ Wholesale Mandi error: {str(e)}")
                finally:
                    if scraper:
                        scraper.close()
            
            # Create comparison
            if scrape_hyperpure or scrape_mandi:
                status_text.markdown("### 🔄 Creating grouped comparison view...")
                comparison_df = create_grouped_comparison(hyperpure_df, mandi_df)
                st.session_state['comparison_data'] = comparison_df
                
                status_text.markdown("### ✅ Scraping completed successfully!")
                progress_bar.progress(100)
    
# ... [All your existing code above remains 100% unchanged] ...

    # Display results
    if 'comparison_data' in st.session_state:
        comparison_df = st.session_state['comparison_data']
        hyperpure_df = st.session_state.get('hyperpure_data', pd.DataFrame())
        mandi_df = st.session_state.get('mandi_data', pd.DataFrame())
        
        with results_container:
            st.markdown("---")
            st.header("📊 Price Comparison Results")
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                total = len(hyperpure_df) + len(mandi_df)
                st.metric("Total Items", total)
            with col2:
                st.metric("Hyperpure Items", len(hyperpure_df))
            with col3:
                st.metric("Wholesale Mandi Items", len(mandi_df))
            
            # Download buttons
            st.subheader("📥 Download Data")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_data, excel_data = create_download_link(comparison_df)
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📄 Download CSV",
                    data=csv_data,
                    file_name=f"price_comparison_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col2:
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_data,
                    file_name=f"price_comparison_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            # Side-by-side comparison view
            st.subheader("🔍 Side-by-Side Comparison")
            
            # Search/filter
            search_term = st.text_input("🔎 Search items", "", placeholder="Type to filter items")
            
            # Filter data
            display_df = comparison_df.copy()
            if search_term:
                mask = (
                    (display_df['Hyperpure_Name'].str.contains(search_term, case=False, na=False)) |
                    (display_df['WholesaleMandi_Name'].str.contains(search_term, case=False, na=False)) |
                    (display_df['Group'].str.contains(search_term, case=False, na=False))
                )
                display_df = display_df[mask]
            
            # Display side-by-side
            st.markdown("### 📋 Grouped Comparison Table")
            
            # Show pricing information
            st.info("💡 **Smart Grouping:** Items are automatically grouped by type (e.g., all Cauliflower varieties together). Ungrouped items appear at the end.")
            
            # Show pricing information about Hyperpure bulk tiers
            st.info("💡 **Hyperpure Pricing:** Multiple prices separated by ' | ' indicate bulk pricing tiers (e.g., lower price per kg for larger orders)")
            
            # === FIXED LINE: Safe removal of IsGroupHeader column ===
            columns_to_show = [col for col in display_df.columns if col != 'IsGroupHeader']
            st.dataframe(
                display_df[columns_to_show],
                use_container_width=True,
                height=600,
                column_config={
                    "Group": st.column_config.TextColumn("Group", width="medium"),
                    "Hyperpure_Name": st.column_config.TextColumn("🟢 Hyperpure - Item", width="large"),
                    "Hyperpure_Price": st.column_config.TextColumn("Price", width="medium", help="Multiple prices show bulk discounts"),
                    "Hyperpure_Unit": st.column_config.TextColumn("Unit", width="small"),
                    "WholesaleMandi_Name": st.column_config.TextColumn("🔵 Wholesale Mandi - Item", width="large"),
                    "WholesaleMandi_Price": st.column_config.TextColumn("Price", width="medium"),
                    "WholesaleMandi_Unit": st.column_config.TextColumn("Unit", width="small"),
                }
            )
            
            # Count groups
            num_groups = len(display_df[display_df['Group'].str.len() > 0])
            num_items = len(display_df) - num_groups
            st.info(f"Showing {num_groups} groups with {num_items} items total")
            
            # Individual source data
            with st.expander("📊 View Individual Source Data"):
                tab1, tab2 = st.tabs(["🟢 Hyperpure", "🔵 Wholesale Mandi"])
                
                with tab1:
                    if not hyperpure_df.empty:
                        st.dataframe(hyperpure_df, use_container_width=True, height=400)
                        st.caption(f"Total: {len(hyperpure_df)} items")
                    else:
                        st.info("No Hyperpure data available")
                
                with tab2:
                    if not mandi_df.empty:
                        st.dataframe(mandi_df, use_container_width=True, height=400)
                        st.caption(f"Total: {len(mandi_df)} items")
                    else:
                        st.info("No Wholesale Mandi data available")


if __name__ == "__main__":
    main()