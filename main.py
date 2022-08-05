import time
import requests
import os
import math
import logging


LOGGER_BASE_NAME = "raindrop2obsidian"
COLLECTIONS_TO_FETCH = ["24904767", "9569415"]
TOEKN = "PUT RAINDROP TEST TOKEN HERE"
BASE_API_URL = "https://api.raindrop.io/rest/v1"
HEADERS = {'Authorization': f"Bearer {TOEKN}"}
RAINDROPS_PER_PAGE = 50  # 50 is the max value - save API requests
HIGHLIGHTS_DIR = os.path.realpath(r"PUT THE DIRECTORY TO SYNC INTO. NOTE: A SUBFOLDER WILL BE CREATED!")
OBSIDIAN_HIGHLIGHTS_DIR = os.path.join(HIGHLIGHTS_DIR)
COLORS = {
    'blue': "0, 0, 255",
    'brown': "165,42,42",
    'cyan': "0, 255, 255",
    'gray': "220,220,220",
    'green': "0, 255, 0",
    'indigo': "75, 0, 130",
    'orange': "255, 165, 0",
    'pink': "255, 192, 203",
    'purple': "159, 43, 104",
    'red': "255, 0, 0",
    'teal': "0, 128, 128",
    'yellow': "255,255,0",
}


def configure_logger():
    import sys
    logger = logging.getLogger(LOGGER_BASE_NAME)
    logger.setLevel(logging.DEBUG)

    stream_formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    file_formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(filename="raindrop2obsidian.log")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger

def get_logger(module_name: str):
    """ module_name should be `__file__`."""
    logger_name = f"{LOGGER_BASE_NAME}." + os.path.relpath(module_name).split('.py')[0].replace(os.sep, ".")
    return logging.getLogger(logger_name)


def date_time_to_int(date_time: str) -> int:
    import datetime
    date_time_obj = datetime.datetime.fromisoformat(date_time[:-1])  # Remove last character 'z'
    return int(date_time_obj.strftime("%Y%m%d%H%M%S"))


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    import unicodedata
    import re
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def get_collection_by_id(collection_id: int):
    response = requests.get(
        url=f"{BASE_API_URL}/collection/{collection_id}",
        headers=HEADERS
    )
    data = response.json()
    return data['item']

def get_raindrops_by_collections(collections: list):
    raindrops = []
    for collection in collections:
        for page_num in range(0, math.ceil(collection['count'] / RAINDROPS_PER_PAGE)):
            response = requests.get(
                url=f"{BASE_API_URL}/raindrops/{collection['_id']}",
                headers=HEADERS,
                params={
                    'perpage': RAINDROPS_PER_PAGE,
                    'page': page_num,
                }
            )
            data = response.json()
            raindrops.extend(data['items'])
    return raindrops


def create_obsidian_file_from_raindrop_article(raindrop, dir):
    collection_id = raindrop['collectionId']
    raindrop_title = raindrop['title']
    raindrop_id = raindrop['_id']
    raindrop_link = raindrop['link']
    raindrop_link_domain = raindrop['domain']
    raindrop_created = raindrop['created']
    raindrop_last_update = raindrop['lastUpdate']
    raindrop_media = raindrop['media']
    raindrop_cover = raindrop['cover']
    raindrop_highlights = raindrop['highlights']

    md_filename = os.path.join(dir, slugify(raindrop_title)) + ".md"
    if not os.path.isfile(md_filename):
        # File does not exist - create a new file with frontmatter
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write("---\n")
            f.write(f"category: raindrop_article\n")
            f.write(f"collection_id: {collection_id}\n")
            f.write(f"raindrop_id: {raindrop_id}\n")
            f.write(f'banner: "{raindrop_cover}"\n')
            f.write("---\n\n")
            f.write(f"%%\nup:: [[+Highlights]]\n%% \n\n")
            f.write(f"# {raindrop_title}\n")
            f.write(f"### Raindrop Metadata\n")
            f.write(f"title:: {raindrop_title}\n")
            f.write(f"link:: [{raindrop_link_domain}]({raindrop_link})\n")
            f.write(f"created:: {raindrop_created}\n\n")
            if len(raindrop_highlights) > 0:
                f.write("### Highlights\n")
    
            for highlight in raindrop_highlights:
                highlight_id = highlight['_id']
                highlight_created = highlight['created']
                highlight_last_update = highlight['lastUpdate']
                highlight_text = highlight['text']
                highlight_note = highlight['note']
                highlight_color_rgb = COLORS[highlight['color']]
                f.write(f"---\n")
                # Write highlight metadata
                f.write(f"Created: {highlight_created}\n")
                f.write(f"Last Updated: {highlight_last_update}\n")

                # Write highlight text
                f.write(f"```ad-quote\n")
                f.write(f"color: {highlight_color_rgb}\n\n")
                f.write(f"{highlight_text}\n")
                f.write(f"```\n")

                # write highlight note
                f.write(f"```ad-note\n")
                # f.write(f"color: {highlight_color_rgb}\n\n")
                f.write(f"{highlight_note}\n")
                f.write(f"```\n\n")


def fetch_and_create_md_files():
    # Fetch data from raindrop
    collections = [get_collection_by_id(collection_id) for collection_id in COLLECTIONS_TO_FETCH]
    raindrops = get_raindrops_by_collections(collections)

    my_collection_metadata = {} 
    for collection in collections:
        collection_id = collection['_id']
        collection_title = collection['title']
        my_collection_dir = os.path.join(OBSIDIAN_HIGHLIGHTS_DIR, f"{collection_id} - {collection_title}")
        os.makedirs(my_collection_dir, exist_ok=True)
        my_collection_metadata[collection_id] = {
            'obsidian_collection_dir': my_collection_dir,
            'title': collection_title
        }

    for raindrop in filter(lambda raindrop: raindrop['type'] == 'article', raindrops):
        create_obsidian_file_from_raindrop_article(raindrop, dir=my_collection_metadata[raindrop['collectionId']]['obsidian_collection_dir'])


def main():
    logger = get_logger(__file__)
    total_wait = 5 * 60
    print_every = 10  # Seconds
    while True:
        logger.info(f"Syncing new Raindrop articles")
        fetch_and_create_md_files()
        for i in range(0, total_wait, print_every):
            logger.info(f"Fetching again in {(total_wait-i) // 60} minutes and {(total_wait-i)%60} seconds")
            time.sleep(print_every)


if __name__ == "__main__":
    configure_logger()
    main()
