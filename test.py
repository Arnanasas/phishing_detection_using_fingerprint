from pqgrams import tree, pqgrams
from database import PostgreSQLDatabase

import configparser

# Initialize the ConfigParser
config = configparser.ConfigParser()

# Read the .ini file
config.read('config.ini')

# Retrieve the DSN string directly
dsn = config.get('database', 'dsn')

# Initialize the database
db = PostgreSQLDatabase(dsn)


test = tree.Node("a").addkid(tree.Node("b"))
test2 = tree.Node("a").addkid(tree.Node("c"))

profile2 = pqgrams.Profile(test2, 2, 3)

profile = pqgrams.Profile(test, 2, 3)

ed = profile.edit_distance(profile2)

pqgram_profile = [
    ('*', 'a', '*', '*', 'b'),
    ('*', 'a', '*', 'b', '*'),
    ('*', 'a', 'b', '*', '*'),
    ('a', 'b', '*', '*', '*')
]

favicon_path = "path_to_favicon"  # Placeholder for favicon path
domain_name = "asd"
dom_json = str(profile)
favicon_path = "test"
if __name__ == "__main__":
    with db:
        query = """
        SELECT website_hash FROM public.website
        WHERE website_id = 16
        """

        one = db.fetch_profile("facebook_com")


ed1 = profile.edit_distance(pqgram_profile)
print(ed1)
