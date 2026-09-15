"""Offline scanning for cloned repositories and local source trees."""

import shlex
import subprocess
import time
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

from github_dorks.dictionaries import iter_dorks, resolve_dictionaries
from github_dorks.output import create_writer


LANGUAGE_EXTENSIONS = {
    'bash': {'.bash', '.sh'},
    'json': {'.json'},
    'php': {'.php'},
    'python': {'.py'},
    'ruby': {'.rb'},
    'shell': {'.bash', '.fish', '.ksh', '.sh', '.zsh'},
    'yaml': {'.yaml', '.yml'},
}
QUALIFIERS = {'extension', 'filename', 'language', 'path'}


@dataclass
class LocalScanStats:
    queries: int = 0
    matches: int = 0
    files: int = 0
    failures: int = 0
    retries: int = 0
    elapsed_seconds: float = 0.0

    @property
    def exit_code(self):
        return 2 if self.failures else 0


@dataclass(frozen=True)
class Predicate:
    kind: str
    value: str

    def matches(self, path, relative_path, normalized_text):
        value = self.value.casefold()
        if self.kind == 'filename':
            return value in path.name.casefold()
        if self.kind == 'extension':
            return path.suffix.casefold().lstrip('.') == value.lstrip('.')
        if self.kind == 'path':
            return value in relative_path.casefold()
        if self.kind == 'language':
            return path.suffix.casefold() in LANGUAGE_EXTENSIONS.get(value, set())
        return value in normalized_text


@dataclass(frozen=True)
class LocalQuery:
    source: str
    clauses: tuple
    exclusions: tuple

    def matches(self, path, relative_path, normalized_text):
        if any(
            predicate.matches(path, relative_path, normalized_text)
            for predicate in self.exclusions
        ):
            return False
        return all(
            any(
                predicate.matches(path, relative_path, normalized_text)
                for predicate in clause
            )
            for clause in self.clauses
        )

    def snippets(self, text, limit=5):
        needles = {
            predicate.value.casefold()
            for clause in self.clauses
            for predicate in clause
            if predicate.kind == 'content'
        }
        if not needles:
            return []
        matches = []
        for number, line in enumerate(text.splitlines(), 1):
            if any(needle in line.casefold() for needle in needles):
                matches.append(f'{number}: {line.strip()}'[:300])
                if len(matches) == limit:
                    break
        return matches


def parse_query(query):
    """Parse the useful local subset of GitHub code-search syntax."""
    tokens = shlex.split(query)
    clauses = []
    exclusions = []
    join_previous = False
    negate_next = False

    for token in tokens:
        operator = token.upper()
        if operator == 'OR':
            join_previous = True
            continue
        if operator == 'NOT':
            negate_next = True
            continue

        name, separator, value = token.partition(':')
        predicate = Predicate(
            name.casefold() if separator and name.casefold() in QUALIFIERS
            else 'content',
            value if separator and name.casefold() in QUALIFIERS else token,
        )
        if negate_next:
            exclusions.append(predicate)
            negate_next = False
            join_previous = False
        elif join_previous and clauses:
            clauses[-1].append(predicate)
            join_previous = False
        else:
            clauses.append([predicate])

    if negate_next or join_previous:
        raise ValueError(f'incomplete operator in dork: {query}')
    return LocalQuery(
        source=query,
        clauses=tuple(tuple(clause) for clause in clauses),
        exclusions=tuple(exclusions),
    )


def _git_files(root):
    try:
        result = subprocess.run(
            [
                'git', '-C', str(root), 'ls-files', '-z', '--cached', '--others',
                '--exclude-standard',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return None
    if result.returncode:
        return None
    return [
        root / name
        for name in result.stdout.decode(errors='surrogateescape').split('\0')
        if name
    ]


def iter_local_files(target):
    """Yield Git-tracked and non-ignored files, with a filesystem fallback."""
    target = Path(target).resolve()
    if target.is_file():
        yield target, target.name
        return
    if not target.is_dir():
        raise ValueError(f'local scan path is not a file or directory: {target}')

    paths = _git_files(target)
    if paths is None:
        paths = (
            path for path in target.rglob('*')
            if '.git' not in path.parts
        )
    for path in paths:
        if path.is_file() and not path.is_symlink():
            yield path, path.relative_to(target).as_posix()


def _read_text(path, max_file_size):
    if path.stat().st_size > max_file_size:
        return None
    contents = path.read_bytes()
    if b'\0' in contents:
        return None
    return contents.decode('utf-8', errors='replace')


def scan_local(local_path, gh_dorks_file=None, categories=None,
               output_filename=None, output_format=None, force=False,
               quiet=False, verbose=False, max_file_size=1_000_000,
               monotonic=time.monotonic, stdout=None, stderr=None):
    """Scan a local working tree with the bundled or custom dorks."""
    import sys

    if max_file_size <= 0:
        raise ValueError('maximum file size must be greater than zero')
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    root = Path(local_path).resolve()
    excluded_output = Path(output_filename).resolve() if output_filename else None
    sources = resolve_dictionaries(gh_dorks_file, categories)
    queries = [parse_query(dork) for dork in iter_dorks(sources)]
    output_format = output_format or ('csv' if output_filename else 'text')
    stats = LocalScanStats(queries=len(queries))
    started_at = monotonic()
    status_stream = stderr if not output_filename and output_format != 'text' else stdout
    if not quiet:
        status_stream.write(f'Scanning local path: {root}\n')

    output_context = (
        open(output_filename, 'w' if force else 'x', newline='', encoding='utf-8')
        if output_filename else nullcontext(stdout)
    )
    with output_context as output_file:
        writer = create_writer(output_format, output_file)
        writer.start()
        try:
            for path, relative_path in iter_local_files(root):
                if excluded_output and path.resolve() == excluded_output:
                    continue
                try:
                    text = _read_text(path, max_file_size)
                except OSError as error:
                    if verbose and not quiet:
                        status_stream.write(f'Skipping {relative_path}: {error}\n')
                    continue
                if text is None:
                    continue
                stats.files += 1
                normalized_text = text.casefold()
                for query in queries:
                    if query.matches(path, relative_path, normalized_text):
                        stats.matches += 1
                        writer.write({
                            'dork': query.source,
                            'text_matches': query.snippets(text),
                            'path': relative_path,
                            'score': len(query.clauses),
                            'url': path.as_uri(),
                        })
        finally:
            stats.elapsed_seconds = monotonic() - started_at
            writer.finish(stats)

    if not quiet:
        if not stats.matches:
            status_stream.write('No local matches found. Hurray!\n')
        status_stream.write(
            f'Summary: {stats.queries} queries, {stats.matches} matches, '
            f'{stats.files} files, {stats.elapsed_seconds:.1f}s elapsed\n'
        )
    return stats
