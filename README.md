# raindrop2obsidian
Until an [Obsidian](https://obsidian.md) plugin is implemented:<br>
This Python script fetches your raindrops (bookmarks at [raindrop.io](https://raindrop.io)) with their highlights & notes, and writes them to markdown files (potentially to your [Obsidian](https://obsidian.md) vault).


### How to use
1. Generate a Raindrop.io `test_token` by creating an app at https://app.raindrop.io/settings/integrations.
2. `git clone https://github.com/almogtzabari/raindrop2obsidian.git`
3. `pip install -r requirements.txt`.
4. Edit `config.yaml`. In particular, edit:
   1. `access_token` - put your raindrop's app `test_token`.
   2. `target_dir` - put a path to a directory to sync the markdown files into. If given path doesn't exist, it will be created. Also, a sub-directory will be created for each collection.
   3. `collections` - put your raindrop collection ids (can be found at the address bar).
5. `python main.py`

Enjoy.

