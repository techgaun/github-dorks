"""GitHub client construction and reliable code-search execution."""

import os
import time
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from sys import prefix

import github3 as github
from requests import exceptions as requests_exceptions

from github_dorks.output import create_writer


@dataclass
class ScanStats:
    queries: int = 0
    matches: int = 0
    failures: int = 0
    retries: int = 0
    elapsed_seconds: float = 0.0

    @property
    def exit_code(self):
        return 2 if self.failures else 0


def create_client(environ=None):
    """Create a GitHub client from the supported environment variables."""
    environ = os.environ if environ is None else environ
    options = {
        'username': environ.get('GH_USER'),
        'password': environ.get('GH_PWD'),
        'token': environ.get('GH_TOKEN'),
    }
    if environ.get('GH_URL'):
        return github.GitHubEnterprise(url=environ['GH_URL'], **options)
    return github.GitHub(**options)


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


def _header_delay(error, now):
    response = getattr(error, 'response', None)
    headers = getattr(response, 'headers', {}) or {}
    if headers.get('Retry-After'):
        try:
            return max(0.0, float(headers['Retry-After']))
        except (TypeError, ValueError):
            pass
    if headers.get('X-RateLimit-Remaining') == '0' and headers.get('X-RateLimit-Reset'):
        try:
            return max(0.0, float(headers['X-RateLimit-Reset']) - now() + 1)
        except (TypeError, ValueError):
            pass
    return None


def _rate_limit_delay(client, now):
    try:
        search_limit = client.rate_limit()['resources']['search']
        if search_limit['remaining'] == 0:
            return max(0.0, float(search_limit['reset']) - now() + 1)
    except (
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
        github.exceptions.GitHubError,
        requests_exceptions.RequestException,
    ):
        pass
    return None


def _retry_delay(error, client, attempt, now):
    if isinstance(error, github.exceptions.ForbiddenError):
        return _header_delay(error, now) or _rate_limit_delay(client, now)

    server_error = getattr(github.exceptions, 'ServerError', ())
    transient_errors = (
        requests_exceptions.ConnectionError,
        requests_exceptions.Timeout,
    )
    if isinstance(error, transient_errors) or (
        server_error and isinstance(error, server_error)
    ):
        return min(2 ** attempt, 30)
    return None


def iter_search_results(client, query, stats, max_retries=3,
                        sleep=time.sleep, now=time.time, stderr=None):
    """Iterate results while retrying bounded, recoverable API failures."""
    results = None
    attempts = 0
    while True:
        try:
            if results is None:
                results = iter(client.search_code(query))
            yield next(results)
        except StopIteration:
            return
        except Exception as error:
            delay = _retry_delay(error, client, attempts, now)
            if delay is None or attempts >= max_retries:
                raise
            attempts += 1
            stats.retries += 1
            if stderr is not None:
                stderr.write(
                    f'Retrying query after {delay:.1f}s '
                    f'({attempts}/{max_retries}): {query}\n'
                )
            sleep(delay)


def _result_record(result, query):
    return {
        'dork': query,
        'text_matches': result.text_matches,
        'path': result.path,
        'score': result.score,
        'url': result.html_url,
    }


def search(repo_to_search=None, user_to_search=None, gh_dorks_file=None,
           output_filename=None, output_format=None, force=False,
           quiet=False, verbose=False, client=None, max_retries=3,
           sleep=time.sleep, now=time.time, monotonic=time.monotonic,
           stdout=None, stderr=None):
    """Run every dork and return statistics, isolating per-query failures."""
    import sys

    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    if bool(repo_to_search) == bool(user_to_search):
        raise ValueError('exactly one repository or user scope is required')
    client = create_client() if client is None else client
    dorks_path = find_dorks_file(gh_dorks_file)
    output_format = output_format or ('csv' if output_filename else 'text')
    stats = ScanStats()
    started_at = monotonic()
    scope = f' repo:{repo_to_search}' if repo_to_search else f' user:{user_to_search}'
    label = 'Repo' if repo_to_search else 'User'
    status_stream = stderr if not output_filename and output_format != 'text' else stdout
    if not quiet:
        status_stream.write(f'Scanning {label}: {scope.split(":", 1)[1]}\n')

    output_context = (
        open(
            output_filename, 'w' if force else 'x', newline='', encoding='utf-8'
        ) if output_filename else nullcontext(stdout)
    )
    with dorks_path.open(encoding='utf-8') as dork_file, output_context as output_file:
        writer = create_writer(output_format, output_file)
        writer.start()
        try:
            for line in dork_file:
                dork = line.strip()
                if not dork or dork[0] in '#;':
                    continue
                query = dork + scope
                stats.queries += 1
                if verbose and not quiet:
                    status_stream.write(f'Searching: {query}\n')
                results = iter_search_results(
                    client, query, stats, max_retries, sleep, now, stderr
                )
                while True:
                    try:
                        result = next(results)
                    except StopIteration:
                        break
                    except Exception as error:
                        authentication_error = getattr(
                            github.exceptions, 'AuthenticationFailed', ()
                        )
                        if authentication_error and isinstance(
                            error, authentication_error
                        ):
                            raise
                        stats.failures += 1
                        stderr.write(f'Query failed: {query}\n{error}\n')
                        break
                    stats.matches += 1
                    writer.write(_result_record(result, query))
        finally:
            stats.elapsed_seconds = monotonic() - started_at
            writer.finish(stats)

    if not quiet:
        if not stats.matches and not stats.failures:
            status_stream.write(f'No results for your dork search{scope}. Hurray!\n')
        status_stream.write(
            f'Summary: {stats.queries} queries, {stats.matches} matches, '
            f'{stats.failures} failures, {stats.retries} retries, '
            f'{stats.elapsed_seconds:.1f}s elapsed\n'
        )
    return stats
