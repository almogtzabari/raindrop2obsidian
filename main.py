import os
import argparse
import yaml
import time
import concurrent.futures
import datetime
import logging
import pyraindropio


MIN2SEC = 60
MB = 2**20
LOGGER_BASE_NAME = 'raindrop2obsidian'


parser = argparse.ArgumentParser(
    description='Raindrop.io highlights to Obsidian.md'
)

parser.add_argument(
    '-c', '--config-filename',
    type=str,
    default="config.yaml",
    dest='config_filename',
    help='Path to config file.'
)


def configure_logger():
    import sys
    from logging.handlers import RotatingFileHandler
    logger = logging.getLogger(LOGGER_BASE_NAME)
    logger.setLevel(logging.DEBUG)

    stream_formatter = logging.Formatter('%(asctime)s - %(message)s', "%H:%M:%S")
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    file_formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    file_handler = RotatingFileHandler(filename=f"{LOGGER_BASE_NAME}.log", maxBytes=1*MB)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger

def get_logger(module_name: str):
    """ module_name should be `__file__`."""
    logger_name = f"{LOGGER_BASE_NAME}." + os.path.relpath(module_name).replace('.py', '').replace(os.sep, ".")
    return logging.getLogger(logger_name)


def wait(total_time_in_sec, report_every_in_sec: int=5):
    for time_passed in range(0, total_time_in_sec, report_every_in_sec):
        time_left_in_sec = total_time_in_sec - time_passed
        print(f"Syncing again in {time_left_in_sec // 60:02}:{time_left_in_sec % 60:02}", end='\r')
        time.sleep(report_every_in_sec)
    

def sync_raindrop(raindrop, md_filename: str) -> None:
    note_last_update = None
    if not os.path.isfile(md_filename):
        note_last_update = '2000-01-01T00:00:00.000Z'
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f'category: "raindrop_article"\n')
            f.write(f'collection_id: "{raindrop.collection["$id"]}"\n')
            f.write(f'raindrop_id: "{raindrop.id}"\n')
            f.write(f'title: "{raindrop.title}"\n')
            f.write(f'link: "{raindrop.link})"\n')
            f.write(f'tags: "{", ".join(raindrop.tags)}"\n')
            f.write(f'created: "{raindrop.created}"\n')
            f.write(f'last_update: "{raindrop.last_update}"\n\n')
            f.write("---\n\n")
            f.write(f"%%\n")
            f.write(f"up:: [[+Highlights]]\n")
            f.write(f"%%\n\n")
            f.write(f'![]({raindrop.cover})\n')
            f.write(f"# {raindrop.title} [{raindrop.domain}]({raindrop.link})\n")

            f.write("### Highlights\n")

    else:
        original_file = md_filename
        temp_file = f"{md_filename}.temp"
        with open(original_file, "r", encoding="utf-8") as f_orig:
            with open(temp_file, 'w', encoding="utf-8") as f_temp:
                for line in f_orig.readlines():
                    if line.startswith('last_update:'):
                        note_last_update = line.split(": ")[-1].strip()
                        line = line.replace(note_last_update, raindrop.last_update)
                    f_temp.write(line)
        
        while True:
            try:
                os.replace(temp_file, original_file)
                break
            except:
                continue
               
    with open(md_filename, 'a', encoding='utf-8') as f:
        for highlight in raindrop.highlights:
            if date_time_to_int(highlight.created) <= date_time_to_int(note_last_update):
                # Highlight was already synced earlier
                continue

            f.write(f"---\n")
            f.write(f"Created: {highlight.created}\n")
            f.write(f"> [!highlight-{highlight.color}]\n")
            highlight_text = highlight.text.replace('\n', '\n> ')
            f.write(f"> {highlight_text}\n\n")

            if highlight.note != '':
                f.write(f"> [!note]\n")
                f.write(f"> {highlight.note}\n\n")


def find_valid_filename(orig, sep: str="-"):
    ret = slugify(orig)
    ret = sep.join(word.capitalize() for word in ret.split("-"))
    return ret


def date_time_to_int(date_time: str) -> int:
    date_time_obj = datetime.datetime.fromisoformat(date_time[:-1])  # Remove last character 'z'
    return int(date_time_obj.strftime("%Y%m%d%H%M%S"))


def fix_problematic_strings(value: str, allow_unicode: bool=False) -> str:
    import unicodedata
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return value

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    import re
    value = fix_problematic_strings(value, allow_unicode=allow_unicode)
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def main(args):
    logger = get_logger(__name__)
    logger.debug(f'Reading config from "{args.config_filename}"')
    with open(args.config_filename, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    logger.debug(f'Config loaded successfully!')
    logger.info(f"'{config['target_dir']}' will be used as target directory")
    os.makedirs(config['target_dir'], exist_ok=True)
    access_token = config['access_token']
    max_threads = config['max_threads']
    session = pyraindropio.Session(access_token=access_token, max_threads=max_threads)
    collections = [session.get_collection_by_id(collection_id) for collection_id in config['collections']]
    while True:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            for collection in collections:
                for raindrop in collection.fetch_all_raindrops():
                    logger.info(f"Syncing {fix_problematic_strings(collection.title)}: {fix_problematic_strings(raindrop.title)}")
                    collection_dir = os.path.join(
                        os.path.realpath(config['target_dir']),
                        find_valid_filename(collection.title)
                    )
                    os.makedirs(collection_dir, exist_ok=True)
                    md_filename = os.path.join(
                        collection_dir,
                        f"{raindrop.id} - " + find_valid_filename(raindrop.title)
                    ) + ".md"
                    executor.submit(sync_raindrop, raindrop=raindrop, md_filename=md_filename)
                
        logger.info(f"Done syncing")
        logger.info(f"Syncing again in {config['sync_every']} minutes")
        wait(config['sync_every'] * MIN2SEC, report_every_in_sec=1)

        
if __name__ == '__main__':
    args = parser.parse_args()
    configure_logger()
    main(args)

    
    
