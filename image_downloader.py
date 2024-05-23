import os
import requests
from urllib.parse import urljoin, urlparse


class ImageDownloader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ImageDownloader, cls).__new__(cls)
        return cls._instance

    def download_images(self, image_urls, folder_name, domain_name):
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        for index, image_url in enumerate(image_urls):
            self._download_image(image_url, folder_name,
                                 f"{domain_name}-{index}")

    def download_favicon(self, favicon_url, folder_name, domain_name):
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        self._download_image(favicon_url, folder_name, domain_name)

    def _download_image(self, url, folder_name, image_name):
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                file_extension = self._get_file_extension(url)
                image_path = os.path.join(
                    folder_name, f"{image_name}{file_extension}")
                with open(image_path, 'wb') as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                print(f"Downloaded: {image_path}")
            else:
                print(
                    f"Failed to download {url}: Status code {response.status_code}")
        except Exception as e:
            print(f"Error downloading {url}: {e}")

    def _get_file_extension(self, url):
        parsed_url = urlparse(url)
        _, file_extension = os.path.splitext(parsed_url.path)
        if not file_extension:
            return '.jpg'  # Default to jpg if no extension is found
        return file_extension
