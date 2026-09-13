"""Discovery and loading for bundled and custom dork dictionaries."""

from importlib.resources import files
from pathlib import Path
from sys import prefix


def category_files():
    directory = files('github_dorks').joinpath('dorks')
    return {
        item.name.removesuffix('.txt'): item
        for item in directory.iterdir()
        if item.name.endswith('.txt')
    }


def available_categories():
    return tuple(sorted(category_files()))


def find_dorks_file(filename=None):
    candidates = []
    if filename:
        candidates.append(Path(filename))
    else:
        candidates.extend([
            Path('github-dorks.txt'),
            Path(prefix) / 'github-dorks' / 'github-dorks.txt',
        ])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError('the dorks file path is not valid')


def resolve_dictionaries(filename=None, categories=None):
    if filename and categories:
        raise ValueError('a custom dorks file cannot be combined with categories')
    if not categories:
        return (find_dorks_file(filename),)

    bundled = category_files()
    unknown = sorted(set(categories) - set(bundled))
    if unknown:
        choices = ', '.join(sorted(bundled))
        raise ValueError(
            f'unknown categories: {", ".join(unknown)}; choose from {choices}'
        )
    return tuple(bundled[category] for category in dict.fromkeys(categories))


def iter_dorks(sources):
    for source in sources:
        with source.open(encoding='utf-8') as dork_file:
            for line in dork_file:
                dork = line.strip()
                if dork and dork[0] not in '#;':
                    yield dork
