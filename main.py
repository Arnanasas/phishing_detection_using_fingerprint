from selenium_renderer import SeleniumRenderer
from database import PostgreSQLDatabase
from tlp_calculator import TLP_calculator
import configparser
# Example usage
if __name__ == "__main__":

    urls = [
        "https://facebook.com/login"
    ]

    # Initialize the ConfigParser
    config = configparser.ConfigParser()
    config.read('config.ini')
    # Retrieve the DSN string directly
    dsn = config.get('database', 'dsn')

    # Render and save url's
    db = PostgreSQLDatabase(dsn)
    with db:
        # db.create_tables()
        renderer = SeleniumRenderer()
        renderer.render_and_save_url(urls)
        calculator = TLP_calculator()
        calculator.process_urls(urls)
