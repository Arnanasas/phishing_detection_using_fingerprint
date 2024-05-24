import psycopg2
from psycopg2 import sql, extras
import json
import ast
import tldextract
import configparser


class PostgreSQLDatabase:
    _instance = None

    def __new__(cls, config_file='./config.ini'):
        if cls._instance is None:
            cls._instance = super(PostgreSQLDatabase, cls).__new__(cls)
            cls._instance.dsn = cls._get_dsn_from_config(config_file)
            cls._instance.conn = None
        return cls._instance

    @staticmethod
    def _get_dsn_from_config(config_file):
        config = configparser.ConfigParser()

        # Read the .ini file
        config.read('config.ini')

        # Retrieve the DSN string directly
        dsn = config.get('database', 'dsn')
        print(dsn)
        return dsn

    def __enter__(self):
        self.open_connection()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection()

    def open_connection(self):
        try:
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(self.dsn)
        except psycopg2.Error as e:
            print(f"Database connection failed: {e}")
            raise e

    def close_connection(self):
        if self.conn and not self.conn.closed:
            self.conn.close()

    def execute(self, query, params=None):
        with self.conn.cursor() as cur:
            cur.execute(query, params)
        self.conn.commit()

    def fetchone(self, query, params=None):
        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def create_tables(self):
        commands = (
            """
            CREATE TABLE IF NOT EXISTS Website (
                website_id SERIAL PRIMARY KEY,
                website_name VARCHAR(255) NOT NULL,
                website_hash JSON NOT NULL,
                favicon_path VARCHAR(255) NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS Image (
                image_id SERIAL PRIMARY KEY,
                website_id INT NOT NULL,
                image_path VARCHAR(255) NOT NULL,
                FOREIGN KEY (website_id) REFERENCES Website(website_id) ON DELETE CASCADE
            )
            """
        )
        try:
            with self.conn.cursor() as cur:
                for command in commands:
                    cur.execute(command)
            self.conn.commit()
        except psycopg2.Error as e:
            print(f"Failed to create tables: {e}")
            self.conn.rollback()
            raise e

    def insert_website(self, website_name, website_hash, favicon_path):
        query = """
        INSERT INTO Website (website_name, website_hash, favicon_path)
        VALUES (%s, %s, %s) RETURNING website_id
        """
        params = (website_name, json.dumps(website_hash), favicon_path)
        return self.fetchone(query, params)['website_id']

    def insert_image(self, website_id, image_path):
        query = """
        INSERT INTO Image (website_id, image_path)
        VALUES (%s, %s)
        """
        params = (website_id, image_path)
        self.execute(query, params)

    def fetch_profile(self, website_name):
        query = """
        SELECT website_hash FROM Website WHERE website_name = %s
        """
        profile = self.fetchone(query, (website_name,))
        if profile:
            return ast.literal_eval(profile['website_hash'])
        return None

    def strip_domain(self, url):
        extracted = tldextract.extract(url)
        return extracted.domain

    def write_website_data(self, url, website_hash, favicon_path, image_paths):
        stripped_domain = self.strip_domain(url)
        website_id = self.insert_website(
            stripped_domain, website_hash, favicon_path)
        for image_path in image_paths:
            self.insert_image(website_id, image_path)
