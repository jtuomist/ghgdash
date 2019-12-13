import os
import importlib
import glob
import inspect


all_pages = {}


def load_pages():
    from .base import Page

    my_path = os.path.dirname(os.path.abspath(__file__))
    for mod_file in glob.glob(os.path.join(my_path, '*.py')):
        parent_mod, mod_name = mod_file.split('/')[-2:]
        mod_name, _ = os.path.splitext(mod_name)
        if mod_name in ('__init__', 'base', 'hel_buildings'):
            continue

        mod = importlib.import_module('.'.join([parent_mod, mod_name]))
        if hasattr(mod, 'page'):
            page = mod.page
        else:
            members = inspect.getmembers(mod, lambda x: inspect.isclass(x) and issubclass(x, Page) and x is not Page)
            assert len(members) == 1, 'No Page subclasses found in %s' % mod
            page = members[0][1]()

        if page.path:
            assert page.path not in all_pages, '%s already exists' % page.path
            all_pages[page.path] = page


def get_page_for_path(path):
    return all_pages.get(path)


def get_page_for_emission_sector(*sector):
    # Remove None sectors
    sector = tuple([x for x in sector if x])

    for page in all_pages.values():
        if not page.emission_sector:
            continue
        if sector == tuple(page.emission_sector):
            return page
    return None
