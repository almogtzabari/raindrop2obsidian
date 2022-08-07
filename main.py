import os
import argparse
import yaml
import time
import concurrent.futures
import datetime
import pyraindropio


MIN2SEC = 60


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


def wait(total_time_in_sec, report_every_in_sec: int=5):
    for time_passed in range(0, total_time_in_sec, report_every_in_sec):
        time_left_in_sec = total_time_in_sec - time_passed
        print(f"Syncing again in {time_left_in_sec // 60:02}:{time_left_in_sec % 60:02} (MM:SS)", end='\r')
        time.sleep(report_every_in_sec)
    

def sync_raindrop(raindrop, md_filename: str) -> None:
    note_last_update = None
    if not os.path.isfile(md_filename):
        # File does not exist - create a new file with frontmatter
        note_last_update = '2000-01-01T00:00:00.000Z'
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"category: raindrop_article\n")
            f.write(f"collection_id: {raindrop.collection['$id']}\n")
            f.write(f"raindrop_id: {raindrop.id}\n")
            f.write(f'banner: "{raindrop.cover}"\n')
            f.write("---\n\n")
            f.write(f"%%\nup:: [[+Highlights]]\n%% \n\n")
            f.write(f"# {raindrop.title}\n")
            f.write(f"### Raindrop Metadata\n")
            f.write(f"title:: {raindrop.title}\n")
            f.write(f"link:: [{raindrop.domain}]({raindrop.link})\n")
            f.write(f"tags:: {', '.join(raindrop.tags)}\n")
            f.write(f"created:: {raindrop.created}\n")
            f.write(f"last_update:: {raindrop.last_update}\n\n")
            if len(raindrop.highlights) > 0:
                f.write("### Highlights\n")

    else:
        original_file = md_filename
        temp_file = f"{md_filename}.temp"
        with open(original_file, "r", encoding="utf-8") as f_orig:
            with open(temp_file, 'w', encoding="utf-8") as f_temp:
                for line in f_orig.readlines():
                    if line.startswith('last_update::'):
                        note_last_update = line.split(":: ")[-1].strip()
                        line = line.replace(note_last_update, raindrop.last_update)
                    f_temp.write(line)
               
    with open(md_filename, 'a', encoding='utf-8') as f:
        for highlight in raindrop.highlights:
            if date_time_to_int(highlight.created) <= date_time_to_int(note_last_update):
                # Highlight was already synced earlier
                continue

            # highlight_color_rgb = COLORS[highlight['color']]
            f.write(f"---\n")
            # Write highlight metadata
            f.write(f"Created: {highlight.created}\n")

            # Write highlight text
            f.write(f"> [!highlight-{highlight.color}]\n")
            highlight_text_replaced = highlight.text.replace('\n', '\n> ')
            f.write(f"> {highlight_text_replaced}\n\n")

            # write highlight note
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
        value = unicodedata.normalize("NFKC", value)
    else:
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def main(config):
    os.makedirs(config['target_dir'], exist_ok=True)
    access_token = config['access_token']
    max_threads = config['max_threads']
    session = pyraindropio.Session(access_token=access_token, max_threads=max_threads)
    collections = [session.get_collection_by_id(collection_id) for collection_id in config['collections']]
    while True:
        print(f"Syncing, please wait...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            for collection in collections:
                for raindrop in collection.fetch_all_raindrops():
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
                
        print(f"Done syncing")
        wait(config['sync_every'] * MIN2SEC, report_every_in_sec=1)

        
if __name__ == '__main__':
    args = parser.parse_args()
    with open(args.config_filename, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    
    main(config)
