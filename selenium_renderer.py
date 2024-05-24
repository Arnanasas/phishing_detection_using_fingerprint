import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pqgrams import tree
from image_downloader import ImageDownloader
from urllib.parse import urljoin, urlparse
from database import PostgreSQLDatabase
import os
import re
from metaphone import doublemetaphone
import tldextract


class SeleniumRenderer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SeleniumRenderer, cls).__new__(cls)
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument("window-size=1920,1080")
            cls._instance.driver = webdriver.Chrome(options=options)
            cls._instance.downloader = ImageDownloader()
            cls._instance.db = PostgreSQLDatabase()
        return cls._instance

    def render_url(self, url):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body')))
            time.sleep(5)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            domain_name = urlparse(url).netloc
            screenshot_folder = os.path.join(os.getcwd(), "screenshot")
            screenshot_filename = os.path.join(
                screenshot_folder, f"{domain_name}.png")

            # Grab favicon
            favicon_link = self._get_favicon_link(soup)
            if favicon_link:
                favicon_url = urljoin(url, favicon_link)
                self.downloader.download_favicon(
                    favicon_url, 'favicon', domain_name)
            print(f"Favicon link: {favicon_link}")

            # Change this later
            if favicon_link is None:
                favicon_link = 'none'

            # Grab all image URLs
            # Initialize a set to collect unique image URLs
            unique_images = set()

            for img_tag in soup.find_all("img"):
                img_src = img_tag.get("src") or img_tag.get("data-src")
                if img_src and not img_src.lower().endswith(".gif"):
                    # Resolve relative URLs to absolute URLs
                    full_url = urljoin(url, img_src)
                    unique_images.add(full_url)

            image_urls = list(unique_images)
            self.downloader.download_images(image_urls, 'images', domain_name)
            image_paths = [
                f"images/{domain_name}-{index}.png" for index in range(len(image_urls))]

            # Generate and print DOM JSON
            body_element = soup.find('body')
            dom_json = self.element_to_json(body_element)
            print(json.dumps(dom_json, indent=4))
            self.driver.get_screenshot_as_file(screenshot_filename)

            ext = tldextract.extract(url)

            stripped_domain_name = ext.domain

            return {
                'domain_name': domain_name,
                'stripped_domain_name': stripped_domain_name,
                'favicon_path': favicon_link,
                'image_paths': image_paths,
                'dom_json': dom_json
            }
        except Exception as e:
            print(e)
            print(f"URL {url} is not available")

        return None

    def render_and_save_url(self, urls):
        for url in urls:
            data = self.render_url(url)
            if data is not None:
                self.db.write_website_data(
                    url, data['dom_json'], data['favicon_path'], data['image_paths'])

    def _get_favicon_link(self, soup):
        icon_link = soup.find('link', rel=lambda x: x and 'icon' in x.lower())
        return icon_link['href'] if icon_link else None

    def _get_all_image_urls(self, soup):
        image_tags = soup.find_all('img')
        image_urls = list({
            img['src'] for img in image_tags
            if img.has_attr('src') and not img['src'].lower().endswith('.gif')
        })
        return image_urls

    def element_to_json(self, element):
        def should_ignore(element):
            ignored_tags = ["script", "svg", "symbol", "ul", "link"]
            if element.name in ignored_tags:
                return True

            if element.name == "div" and all(
                    child.name == "div" and not child.find_all(recursive=False) for child in element.find_all(recursive=False)):
                return True

            if element.has_attr('role') and element['role'] == "dialog":
                return True

            if element.has_attr('style') and 'display: none' in element['style']:
                return True

            return False

        if should_ignore(element):
            return None

        children = element.find_all(recursive=False)
        children_json = [self.element_to_json(child) for child in children]
        children_json = [child for child in children_json if child is not None]

        return {"label": element.name, "children": children_json}

    def json_to_tree(self, json_data):
        if isinstance(json_data, str):
            json_data = json.loads(json_data)

        root = tree.Node(json_data['label'])
        for child in json_data.get('children', []):
            child_node = self.json_to_tree(child)
            root.addkid(child_node)
        return root

    def render_and_save_url(self, urls, is_phishing):
        for url in urls:
            if not is_phishing:
                data = self.render_url(url)
                if data is not None:
                    primary, secondary = self.double_metaphone(
                        data['stripped_domain_name'])

                    print(primary)
                    print(secondary)
                    website_id = self.db.write_website_data(
                        url, data['dom_json'], data['favicon_path'], data['image_paths'])
                    self.db.insert_soundex(website_id, primary, secondary)
            else:
                self.render_url(url)

    def double_metaphone(self, domain_name):
        """ Clean domain_name from top level domain """
        domain_name_cleared = re.sub(r'[„“”]', '', domain_name)
        if '.' in domain_name_cleared:
            # Split the domain name by '.'
            parts = domain_name_cleared.split('.')
            parts = parts[:-1]
            name = '.join(parts)'
        else:
            # if the name is empty after removal of last array item, keep as it is
            name = domain_name_cleared

        # Compute the double metaphone values
        primary, secondary = doublemetaphone(name)
        return (primary, secondary)
