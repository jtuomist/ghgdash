import os
import importlib
import glob
import inspect
from .base import Page

all_pages = {}


def load_pages():
    my_path = os.path.dirname(os.path.abspath(__file__))
    for mod_file in glob.glob(os.path.join(my_path, '*.py')):
        parent_mod, mod_name = mod_file.split('/')[-2:]
        mod_name, _ = os.path.splitext(mod_name)
        if mod_name in ('__init__', 'base', 'hel_buildings', 'routing'):
            continue

        mod = importlib.import_module('.'.join([parent_mod, mod_name]))
        if hasattr(mod, 'page'):
            page = mod.page
            assert page.path, 'No path for page %s' % page
            assert page.path not in all_pages, '%s already exists' % page.path
            all_pages[page.path] = page
        else:
            members = inspect.getmembers(mod, lambda x: inspect.isclass(x) and issubclass(x, Page) and x is not Page)
            assert len(members) == 1, 'No Page subclasses found in %s' % mod
            page_class = members[0][1]
            assert page_class.path not in all_pages, '%s already exists' % page.path
            assert page_class.path, 'No path for page %s' % page_class
            all_pages[page_class.path] = page_class


def page_instance(page):
    if isinstance(page, Page):
        return page
    assert issubclass(page, Page)
    return page()


def get_page_for_emission_sector(*sector):
    if not all_pages:
        load_pages()
    # Remove None sectors
    sector = tuple([x for x in sector if x])

    for page in all_pages.values():
        if not page.emission_sector:
            continue
        if sector == tuple(page.emission_sector):
            return page_instance(page)
    return None
