import json
import os
import shutil
from urllib.parse import urlparse
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pqgrams import pqgrams, tree
from image_downloader import ImageDownloader
from database import PostgreSQLDatabase
from urllib.parse import urljoin, urlparse
from imagededup.methods import CNN, PHash

import logging

import warnings
from tqdm import tqdm

# Suppress warnings from „imagededup” logging
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning, module='torchvision')
tqdm = lambda *args, **kwargs: None
logging.getLogger('imagededup').setLevel(logging.CRITICAL)
logging.getLogger('torchvision').setLevel(logging.CRITICAL)
logging.getLogger('tensorflow').setLevel(logging.CRITICAL)
logging.getLogger('PIL').setLevel(logging.CRITICAL)
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)


class TLP_calculator:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TLP_calculator, cls).__new__(cls)
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
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body')))
        time.sleep(5)

        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        domain_name = urlparse(url).netloc

        # Define screenshot filename
        screenshot_folder = os.path.join(os.getcwd(), "screenshot")
        screenshot_filename = os.path.join(
            screenshot_folder, f"{domain_name}.png")

        # Generate DOM JSON
        body_element = soup.find('body')
        dom_json = self.element_to_json(body_element)

        favicon_link = self._get_favicon_link(soup)
        if favicon_link:
            favicon_url = urljoin(url, favicon_link)
            self.downloader.download_favicon(
                favicon_url, 'favicon', domain_name)
        print(f"Favicon link: {favicon_link}")

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
            f"{domain_name}-{index}.png" for index in range(len(image_urls))]

        # Calculate and print smallest pq_gram distance
        self.calculate_smallest_pqgram_distance(dom_json, domain_name)

        # Check for favicon duplicates
        if favicon_link:
            favicon_path = os.path.join('favicon', f"{domain_name}.png")
            f2_result = self.check_favicon_duplicates(favicon_path, 'favicon')
            print(f"Feature F2 (Favicon duplicates): {f2_result}")

        # Check for image duplicates
        if image_paths:
            f3_result = self.check_image_duplicates('images', image_paths)
            print(f"Feature F3 (Image duplicates): {f3_result}")

        screenshot = self.driver.get_screenshot_as_file(screenshot_filename)

        if screenshot:
            screenshot_path = os.path.join('screenshot', f"{domain_name}.png")
            f4_result = self.check_favicon_duplicates(
                screenshot_path, 'screenshot')
            print(f"Feature F4 (Screenshot duplicates): {f4_result}")

        # Cleanup images after calculation
        self.delete_images([f"{domain_name}.png"], './screenshot')
        self.delete_images(image_paths, './images')
        self.delete_images([f"{domain_name}.png"], './favicon')

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

    def calculate_smallest_pqgram_distance(self, dom_json, domain_name):
        with self.db as db:
            db.open_connection()
            get_all_website_hashes = """
                SELECT website_hash FROM public.website;
                """
            website_hashes = self.db.fetch_all(get_all_website_hashes)
            current_tree = self.json_to_tree(dom_json)
            current_profile = pqgrams.Profile(current_tree, 2, 3)

            min_distance = float('inf')

            for hash in website_hashes:
                this_tree = self.json_to_tree(hash[0])
                db_profile = pqgrams.Profile(this_tree, 2, 3)
                distance = current_profile.edit_distance(db_profile)
                if distance < min_distance:
                    min_distance = distance

            print(f"Smallest pq_gram distance: {min_distance}")

    def delete_images(self, image_list, base_dir):
        for image_path in image_list:
            # Create the full path to the image
            full_path = os.path.join(base_dir, image_path)

            try:
                # Delete the image file if it exists
                if os.path.isfile(full_path):
                    os.remove(full_path)
                    print(f"Deleted: {full_path}")
                else:
                    print(f"File not found: {full_path}")
            except Exception as e:
                print(f"Error deleting {full_path}: {e}")

    def process_urls(self, urls):
        for url in urls:
            self.render_url(url)

    def check_favicon_duplicates(self, favicon_path, base_dir):
        hasher = CNN()
        if os.path.exists(favicon_path):
            return self.check_for_duplicates(hasher, base_dir, [os.path.basename(favicon_path)])
        return 0

    def check_image_duplicates(self, base_dir, image_paths):
        hasher = PHash()
        image_names = [os.path.basename(path) for path in image_paths]
        return self.check_for_duplicates(hasher, base_dir, image_names)

    def check_for_duplicates(self, hasher, image_dir, image_names):
        # Generate encodings for all images in the specified directory
        encodings = hasher.encode_images(image_dir=image_dir)
        duplicates = hasher.find_duplicates(encoding_map=encodings)

        # Check if any of the specified images have duplicates
        for image_name in image_names:
            if image_name in duplicates and duplicates[image_name]:
                # print(f"{image_name} duplicates: {duplicates[image_name]}")
                return 1
        return 0
