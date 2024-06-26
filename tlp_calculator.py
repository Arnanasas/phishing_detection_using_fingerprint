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
import ssl
import socket
import re
from metaphone import doublemetaphone
import csv

from helpers import get_tlp_value

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
        f1_result = None
        f2_result = None
        f3_result = None
        f4_result = None
        f5_result = None
        f6_result = None
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

        # Extract title to words
        title_tag = soup.title
        title_words = title_tag.get_text().split() if title_tag else []
        print(title_words)

        # Calculate and print smallest pq_gram distance
        f1_result = self.calculate_smallest_pqgram_distance(
            dom_json, domain_name)

        # Check for favicon duplicates
        if favicon_link:
            favicon_path = os.path.join('favicon', f"{domain_name}.png")
            f2_result = self.check_favicon_duplicates(favicon_path, 'favicon')

        # Check for image duplicates
        if image_paths:
            f3_result = self.check_image_duplicates('images', image_paths)

        screenshot = self.driver.get_screenshot_as_file(screenshot_filename)

        if screenshot:
            screenshot_path = os.path.join('screenshot', f"{domain_name}.png")
            f4_result = self.check_favicon_duplicates(
                screenshot_path, 'screenshot')

        # Calculate SSL issuer feature
        f5_result = self.check_ssl_issuer(url)

        f6_result = self.process_and_check_titles(title_words)

        # Cleanup images after calculation
        self.delete_images([f"{domain_name}.png"], './screenshot')
        self.delete_images(image_paths, './images')
        self.delete_images([f"{domain_name}.png"], './favicon')

        print("Features values:")
        print(f"Smallest pq_gram distance: {f1_result}")
        print(f"Feature F2 (Favicon duplicates): {f2_result}")
        print(f"Feature F3 (Image duplicates): {f3_result}")
        print(f"Feature F4 (Screenshot duplicates): {f4_result}")
        print(f"Feature F5 (SSL issuer): {f5_result}")
        print(f"Feature F6 (Phonetic algorithm): {f6_result}")

        risk_index, weighted_features = self.calculate_risk_index(
            domain_name, f1_result, f2_result, f3_result, f4_result, f5_result, f6_result)

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

    def calculate_risk_index(self, domain_name, f1, f2, f3, f4, f5, f6):
        # Ensure all features have values
        if f1 is None:
            raise ValueError("Feature 1 must exist.")
        if f2 is None:
            f2 = 0.5
        if f3 is None or f4 is None or f5 is None:
            raise ValueError("Features 3-5 must exist.")
        if f6 is None:
            f6 = 0
        elif isinstance(f6, list) and len(f6) > 0:
            f6 = 1
        else:
            f6 = 0

        # Define feature weights
        feature_weights = {
            'f1': 2,
            'f2': 1.5,
            'f3': 1.5,
            'f4': 2,
            'f5': 1,
            'f6': 2
        }

        # Calculate weighted features
        weighted_features = {
            'f1': f1 * feature_weights['f1'],
            'f2': f2 * feature_weights['f2'],
            'f3': f3 * feature_weights['f3'],
            'f4': f4 * feature_weights['f4'],
            'f5': f5 * feature_weights['f5'],
            'f6': f6 * feature_weights['f6']
        }

        # Calculate risk index
        risk_index = sum(weighted_features.values())

        # Write results to CSV
        results_path = os.path.join(os.getcwd(), 'results.csv')

        tlp_value = get_tlp_value(risk_index)
        with open(results_path, 'a', newline='') as csvfile:
            fieldnames = ['domain_name', 'risk_index',
                          'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'TLP']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if csvfile.tell() == 0:
                writer.writeheader()

            writer.writerow({
                'domain_name': domain_name,
                'risk_index': risk_index,
                'f1': weighted_features['f1'],
                'f2': weighted_features['f2'],
                'f3': weighted_features['f3'],
                'f4': weighted_features['f4'],
                'f5': weighted_features['f5'],
                'f6': weighted_features['f6'],
                'TLP': tlp_value
            })

        return risk_index, weighted_features

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

            return min_distance

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

    def check_ssl_issuer(self, url):
        try:
            # Extract hostname (remove 'http://' or 'https://')
            hostname = url.replace(
                'http://', '').replace('https://', '').split('/')[0]

            context = ssl.create_default_context()
            with context.wrap_socket(socket.socket(), server_hostname=hostname) as s:
                s.connect((hostname, 443))
                cert = s.getpeercert()

            # Extract the issuer of the certificate
            issuer = dict(x[0] for x in cert['issuer'])
            common_name = issuer.get(
                'commonName', issuer.get('organizationName'))

            # If issuer is R3 (Let's Encrypt)
            if 'R3' in common_name:
                return 0.5
            else:
                return 0
        except Exception as e:
            # If any error occurs assume no certificate
            return 1

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

    def process_and_check_titles(self, words):
        """
        Process the title words, compute their Soundex values, and check for matches in the database.
        """
        primary_values = []
        secondary_values = []

        for word in words:
            primary_hash, secondary_hash = self.double_metaphone(word)
            primary_values.append(primary_hash)
            secondary_values.append(
                secondary_hash if secondary_hash else primary_hash)

        print(primary_values)
        with self.db as db:
            matches = db.check_soundex_matches(
                primary_values, secondary_values)
        return matches
