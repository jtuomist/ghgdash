import quilt
from quilt.tools import store
from quilt.tools.command import _materialize
from quilt.imports import _from_core_node

import importlib
import logging
import collections
from datetime import datetime


logger = logging.getLogger(__name__)


def load_datasets(packages, include_units=False):
    if not isinstance(packages, (list, tuple)):
        packages = [packages]

    datasets = []
    for package_path in packages:
        user, root_pkg, *sub_paths = package_path.split('/')

        pkg_store, root_node = store.PackageStore.find_package(None, user, root_pkg)
        if root_node is None:
            quilt.install(package_path, force=True)
            pkg_store, root_node = store.PackageStore.find_package(None, user, root_pkg)

        node = root_node
        while len(sub_paths):
            name = sub_paths.pop(0)
            for child_name, child_node in node.children.items():
                if child_name != name:
                    continue
                try:
                    node = _from_core_node(pkg_store, child_node)
                except store.StoreException:
                    quilt.install(package_path, force=True)
                    node = _from_core_node(pkg_store, child_node)
                break
            else:
                raise Exception('Dataset %s not found' % package_path)

        try:
            df = node()
        except store.StoreException:
            _materialize(node)
            df = node()

        if include_units:
            for col_name in df.columns:
                unit = node._meta.get('%s_unit' % col_name, None)
                if not unit:
                    continue
                df[col_name] = df[col_name].astype('pint[%s]' % unit)

        datasets.append(df)

    if len(datasets) == 1:
        return datasets[0]

    return datasets
