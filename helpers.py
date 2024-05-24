import csv


def get_urls_by_target(file_path, target, start, end):
    """
    Extracts and returns a specified range of URLs that match a given target from a CSV file.

    Parameters:
        file_path (str): Path to the CSV file.
        target (str): The specific target name to filter URLs by.
        start (int): The starting index (inclusive) of the range.
        end (int): The ending index (exclusive) of the range.

    Returns:
        list: List of URLs matching the specified target within the specified range.
    """
    urls = []
    with open(file_path, mode='r', newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if row['target'] == target:
                urls.append(row['url'])

    return urls[start:end]
