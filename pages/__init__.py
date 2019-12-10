import os
import importlib
import glob


all_pages = {}


def load_pages():
    my_path = os.path.dirname(os.path.abspath(__file__))
    for mod_file in glob.glob(os.path.join(my_path, '*.py')):
        parent_mod, mod_name = mod_file.split('/')[-2:]
        mod_name, _ = os.path.splitext(mod_name)
        if mod_name in ('__init__', 'base', 'hel_buildings'):
            continue

        mod = importlib.import_module('.'.join([parent_mod, mod_name]))
        page = mod.page
        if page.path:
            all_pages[page.path] = page


def get_page_for_path(path):
    return all_pages.get(path)


def get_page_for_emission_sector(sector1, sector2):
    if not sector2:
        sector2 = None
    for page in all_pages.values():
        if not page.emission_sector:
            continue
        if (sector1, sector2) == tuple(page.emission_sector):
            return page
    return None
