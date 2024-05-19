import os
import requests
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from pathlib import Path
import json
from database import PostgreSQLDatabase
from pqgrams import tree, pqgrams


class SeleniumRenderer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SeleniumRenderer, cls).__new__(cls)
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            cls._instance.driver = webdriver.Chrome(options=options)
        return cls._instance

    def render_url(self, url):
        self.driver.get(url)
        dom_structure = self.driver.find_element(
            By.TAG_NAME, 'body').get_attribute('outerHTML')
        return dom_structure

    def download_image(self, img_url, domain_name, index):
        response = requests.get(img_url, stream=True)
        if response.status_code == 200:
            image_path = f"{domain_name}-{index}.jpg"
            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return image_path
        return None

    def element_to_json(self, element):
        """
        Extracts and returns a json tree from HTML DOM.
        Parameters:
            element: root HTML DOM element (eg. <body>)
        Returns:
            json: DOM tree structure: label, children.        
        """
        def should_ignore(element):
            # Ignore specific tags
            ignored_tags = ["script", "svg", "symbol", "ul", "link"]
            if element.name in ignored_tags:
                return True

            # Ignore empty `div`s
            if element.name == "div" and all(
                    child.name == "div" and not child.find_all(recursive=False) for child in element.find_all(recursive=False)):
                return True

            # Ignore elements with `role="dialog"`
            if element.has_attr('role') and element['role'] == "dialog":
                return True

            # Ignore elements with `display: none` styling
            if element.has_attr('style') and 'display: none' in element['style']:
                return True

            return False

        # Recursively ignore unwanted elements
        if should_ignore(element):
            return None

        children = element.find_all(recursive=False)
        children_json = [self.element_to_json(child) for child in children]
        # Filter out None values
        children_json = [child for child in children_json if child is not None]

        # Return the JSON-like structure
        return {"label": element.name, "children": children_json}

    def json_to_tree(self, json_data):
        """ Convert JSON object to a tree structure using the tree.Node class from pqgrams. """
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        # Create the root node from the label
        root = tree.Node(json_data['label'])
        # Iterate over children if any
        for child in json_data.get('children', []):
            child_node = self.json_to_tree(child)
            root.addkid(child_node)
        return root

    def tree_to_profilejson(self, json_data):
        """ Create profile from json tree """
        tree_root = self.json_to_tree(json_data)
        profile = pqgrams.Profile(tree_root, 2, 3)
        return str(profile)

    def process_urls(self, urls, db):
        for url, is_phishing in urls:
            print(f"Processing URL: {url} | Is Phishing: {is_phishing}")
            parsed_url = urlparse(url)
            domain_name = parsed_url.netloc.replace("www.", "")
            parts = domain_name.split('.')
            parts = parts[:-1]
            domain_name_final = '.'.join(parts)

            dom_structure = self.render_url(url)

            # Parse HTML and download images
            soup = BeautifulSoup(dom_structure, 'html.parser')
            images = soup.find_all('img')
            image_paths = []
            for index, img in enumerate(images):
                img_url = img.get('src')
                if not img_url.startswith('http'):
                    img_url = urlparse(url)._replace(
                        path=img_url).geturl()  # Handle relative URLs
                image_path = self.download_image(img_url, domain_name, index)
                if image_path:
                    image_paths.append(image_path)

            print(f"Downloaded {len(image_paths)} images.")

            # Convert DOM to JSON and print it
            body_element = soup.find('body')
            if body_element:
                dom_json = self.element_to_json(body_element)
                print("DOM JSON Structure:")
                # Pretty-print the JSON structure
                print(json.dumps(dom_json, indent=2))

                # Save to database
                favicon_path = "path_to_favicon"  # Placeholder for favicon path
                website_id = db.insert_website(
                    domain_name_final, dom_json, favicon_path)

                for image_path in image_paths:
                    db.insert_image(website_id, image_path)
