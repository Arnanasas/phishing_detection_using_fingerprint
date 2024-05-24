from selenium_renderer import SeleniumRenderer
from database import PostgreSQLDatabase
from tlp_calculator import TLP_calculator
import configparser
from helpers import get_urls_by_target
# Example usage
if __name__ == "__main__":

    # verified phishing dataset is downloaded from PhishTank.org
    file_path = './verified_phishing.csv'
    target = 'Facebook'
    train_urls = get_urls_by_target(file_path, target, 0, 5)
    test_urls = get_urls_by_target(file_path, target, 6, 10)

    # Initialize the ConfigParser
    config = configparser.ConfigParser()
    config.read('config.ini')
    # Retrieve the DSN string directly
    dsn = config.get('database', 'dsn')

    facebook = ['https://facebook.com/login']
    is_phishing = bool(0)
    # Render and save url's
    db = PostgreSQLDatabase(dsn)
    with db:
        db.create_tables()
        # renderer = SeleniumRenderer()
        # renderer.render_and_save_url(facebook, is_phishing)
        calculator = TLP_calculator()
        calculator.process_urls(facebook)
