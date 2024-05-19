from selenium_renderer import SeleniumRenderer
from database import PostgreSQLDatabase
import configparser
# Example usage
if __name__ == "__main__":

    urls = [
        ("https://facebook.com/login", False),
        ("https://facebook.com/login", True)
    ]

    # Initialize the ConfigParser
    config = configparser.ConfigParser()

    # Read the .ini file
    config.read('config.ini')

    # Retrieve the DSN string directly
    dsn = config.get('database', 'dsn')

    # Initialize the database
    db = PostgreSQLDatabase(dsn)
    with db:
        db.create_tables()
        renderer = SeleniumRenderer()
        renderer.process_urls(urls, db)
