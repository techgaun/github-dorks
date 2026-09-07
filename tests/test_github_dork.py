import csv
import io
import json
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


class FakeGitHubError(Exception):
    pass


class FakeForbiddenError(FakeGitHubError):
    pass


class FakeServerError(FakeGitHubError):
    pass


class FakeAuthenticationFailed(FakeGitHubError):
    pass


fake_github3 = types.ModuleType('github3')
fake_github3.GitHub = lambda **kwargs: None
fake_github3.GitHubEnterprise = lambda **kwargs: None
fake_github3.exceptions = types.SimpleNamespace(
    ForbiddenError=FakeForbiddenError,
    GitHubError=FakeGitHubError,
    ServerError=FakeServerError,
    AuthenticationFailed=FakeAuthenticationFailed,
)
sys.modules.setdefault('github3', fake_github3)
sys.modules.setdefault('feedparser', types.ModuleType('feedparser'))

from github_dorks import __version__, cli as github_dork  # noqa: E402
from github_dorks import search as search_module  # noqa: E402


class SearchResult:
    text_matches = ['secret, with comma']
    path = 'config/file.env'
    score = 42
    html_url = 'https://github.example/result'


class GitHubClient:
    def search_code(self, query):
        self.query = query
        return iter([SearchResult()])


class SequenceIterator:
    def __init__(self, events):
        self.events = iter(events)

    def __iter__(self):
        return self

    def __next__(self):
        event = next(self.events)
        if isinstance(event, Exception):
            raise event
        return event


class SearchTests(unittest.TestCase):
    def test_creates_public_github_client_from_environment(self):
        environment = {'GH_USER': 'user', 'GH_PWD': 'password', 'GH_TOKEN': 'token'}
        with patch.object(search_module.github, 'GitHub') as factory:
            search_module.create_client(environment)

        factory.assert_called_once_with(
            username='user', password='password', token='token'
        )

    def test_creates_enterprise_client_from_environment(self):
        environment = {'GH_URL': 'https://github.example', 'GH_TOKEN': 'token'}
        with patch.object(search_module.github, 'GitHubEnterprise') as factory:
            search_module.create_client(environment)

        factory.assert_called_once_with(
            url='https://github.example', username=None, password=None,
            token='token',
        )

    def test_writes_valid_csv_and_scopes_query_to_repository(self):
        client = GitHubClient()
        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            output = Path(directory) / 'results.csv'
            dorks.write_text('# comment\nfilename:.env PASSWORD\n', encoding='utf-8')

            stats = github_dork.search(
                repo_to_search='owner/repo',
                gh_dorks_file=str(dorks),
                output_filename=str(output),
                client=client,
            )

            with output.open(newline='', encoding='utf-8') as output_file:
                rows = list(csv.reader(output_file))

        self.assertEqual(client.query, 'filename:.env PASSWORD repo:owner/repo')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], 'Issue Type (Dork)')
        self.assertEqual(rows[1][0], client.query)
        self.assertEqual(rows[1][1], "['secret, with comma']")
        self.assertEqual(stats.matches, 1)
        self.assertEqual(stats.exit_code, 0)

    def test_streams_json_document_to_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            dorks.write_text('query\n', encoding='utf-8')
            stdout = io.StringIO()
            stderr = io.StringIO()
            github_dork.search(
                repo_to_search='owner/repo', gh_dorks_file=str(dorks),
                output_format='json', client=GitHubClient(),
                stdout=stdout, stderr=stderr, monotonic=lambda: 10,
            )

        document = json.loads(stdout.getvalue())
        self.assertEqual(document['results'][0]['path'], SearchResult.path)
        self.assertEqual(document['summary']['matches'], 1)
        self.assertNotIn('Scanning', stdout.getvalue())
        self.assertIn('Summary: 1 queries, 1 matches', stderr.getvalue())

    def test_streams_typed_json_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            dorks.write_text('query\n', encoding='utf-8')
            stdout = io.StringIO()
            github_dork.search(
                repo_to_search='owner/repo', gh_dorks_file=str(dorks),
                output_format='jsonl', quiet=True, client=GitHubClient(),
                stdout=stdout, stderr=io.StringIO(),
            )

        records = [json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual([record['type'] for record in records], ['result', 'summary'])
        self.assertEqual(records[1]['matches'], 1)

    def test_quiet_suppresses_status_but_not_text_results(self):
        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            dorks.write_text('query\n', encoding='utf-8')
            stdout = io.StringIO()
            github_dork.search(
                repo_to_search='owner/repo', gh_dorks_file=str(dorks),
                quiet=True, client=GitHubClient(), stdout=stdout,
            )

        self.assertIn('Found result', stdout.getvalue())
        self.assertNotIn('Scanning', stdout.getvalue())
        self.assertNotIn('Summary', stdout.getvalue())

    def test_refuses_to_overwrite_output_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            output = Path(directory) / 'results.json'
            dorks.write_text('query\n', encoding='utf-8')
            output.write_text('keep me', encoding='utf-8')

            with self.assertRaises(FileExistsError):
                github_dork.search(
                    repo_to_search='owner/repo', gh_dorks_file=str(dorks),
                    output_filename=str(output), output_format='json',
                    client=GitHubClient(),
                )
            self.assertEqual(output.read_text(encoding='utf-8'), 'keep me')

            github_dork.search(
                repo_to_search='owner/repo', gh_dorks_file=str(dorks),
                output_filename=str(output), output_format='json', force=True,
                quiet=True, client=GitHubClient(),
            )
            self.assertEqual(json.loads(output.read_text())['summary']['matches'], 1)

    def test_output_failure_is_fatal(self):
        class BrokenStream(io.StringIO):
            def write(self, value):
                raise OSError('disk full')

        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            dorks.write_text('query\n', encoding='utf-8')
            with self.assertRaisesRegex(OSError, 'disk full'):
                github_dork.search(
                    repo_to_search='owner/repo', gh_dorks_file=str(dorks),
                    quiet=True, client=GitHubClient(), stdout=BrokenStream(),
                )

    def test_reports_when_no_results_are_found(self):
        client = GitHubClient()
        client.search_code = lambda query: iter([])
        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            dorks.write_text('filename:.env\n', encoding='utf-8')
            stdout = io.StringIO()
            stats = github_dork.search(
                user_to_search='example', gh_dorks_file=str(dorks),
                client=client, stdout=stdout,
            )

        self.assertIn('No results for your dork search user:example', stdout.getvalue())
        self.assertIn('Summary: 1 queries, 0 matches', stdout.getvalue())
        self.assertEqual(stats.queries, 1)

    def test_rejects_missing_dorks_file_with_clear_error(self):
        with self.assertRaisesRegex(Exception, 'dorks file path is not valid'):
            github_dork.search(
                repo_to_search='owner/repo',
                gh_dorks_file='/does/not/exist', client=GitHubClient(),
            )

    def test_retries_server_error_with_exponential_backoff(self):
        client = GitHubClient()
        client.search_code = lambda query: SequenceIterator([
            FakeServerError('temporary'), FakeServerError('temporary'), SearchResult(),
        ])
        sleeps = []
        stats = search_module.ScanStats()

        results = list(search_module.iter_search_results(
            client, 'query', stats, sleep=sleeps.append,
        ))

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], SearchResult)
        self.assertEqual(sleeps, [1, 2])
        self.assertEqual(stats.retries, 2)

    def test_retries_failure_that_starts_a_search(self):
        client = GitHubClient()
        calls = []

        def start_search(query):
            calls.append(query)
            if len(calls) == 1:
                raise FakeServerError('temporary')
            return iter([SearchResult()])

        client.search_code = start_search
        sleeps = []
        stats = search_module.ScanStats()
        results = list(search_module.iter_search_results(
            client, 'query', stats, sleep=sleeps.append,
        ))

        self.assertEqual(len(results), 1)
        self.assertEqual(calls, ['query', 'query'])
        self.assertEqual(sleeps, [1])

    def test_stops_after_retry_limit(self):
        client = GitHubClient()
        client.search_code = lambda query: SequenceIterator([
            FakeServerError('one'), FakeServerError('two'),
            FakeServerError('three'),
        ])
        sleeps = []
        stats = search_module.ScanStats()

        with self.assertRaises(FakeServerError):
            list(search_module.iter_search_results(
                client, 'query', stats, max_retries=2, sleep=sleeps.append,
            ))

        self.assertEqual(sleeps, [1, 2])
        self.assertEqual(stats.retries, 2)

    def test_waits_until_search_rate_limit_resets(self):
        error = FakeForbiddenError('rate limited')
        client = GitHubClient()
        client.search_code = lambda query: SequenceIterator([error, SearchResult()])
        client.rate_limit = lambda: {
            'resources': {'search': {'remaining': 0, 'reset': 109}}
        }
        sleeps = []
        stats = search_module.ScanStats()

        list(search_module.iter_search_results(
            client, 'query', stats, sleep=sleeps.append, now=lambda: 100,
        ))

        self.assertEqual(sleeps, [10])

    def test_continues_after_a_query_fails(self):
        class MixedClient:
            def search_code(self, query):
                if query.startswith('bad'):
                    return SequenceIterator([FakeGitHubError('invalid query')])
                return iter([SearchResult()])

        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            dorks.write_text('bad\ngood\n', encoding='utf-8')
            stdout = io.StringIO()
            stderr = io.StringIO()
            stats = github_dork.search(
                repo_to_search='owner/repo', gh_dorks_file=str(dorks),
                client=MixedClient(), stdout=stdout, stderr=stderr,
            )

        self.assertEqual(stats.queries, 2)
        self.assertEqual(stats.matches, 1)
        self.assertEqual(stats.failures, 1)
        self.assertEqual(stats.exit_code, 2)
        self.assertIn('Query failed: bad repo:owner/repo', stderr.getvalue())

    def test_authentication_failure_is_fatal(self):
        client = GitHubClient()
        client.search_code = lambda query: SequenceIterator([
            FakeAuthenticationFailed('bad credentials')
        ])
        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            dorks.write_text('query\n', encoding='utf-8')
            with self.assertRaises(FakeAuthenticationFailed):
                github_dork.search(
                    repo_to_search='owner/repo', gh_dorks_file=str(dorks),
                    client=client,
                )


class CommandLineTests(unittest.TestCase):
    def test_parses_output_controls(self):
        arguments = [
            '-r', 'owner/repo', '--format', 'json', '--output', 'results.json',
            '--force', '--verbose',
        ]
        args = github_dork.build_parser().parse_args(arguments)

        self.assertEqual(args.output_format, 'json')
        self.assertEqual(args.output_filename, 'results.json')
        self.assertTrue(args.force)
        self.assertTrue(args.verbose)

    def test_version_comes_from_package_metadata(self):
        stdout = io.StringIO()
        with patch.object(sys, 'argv', ['github-dorks', '--version']):
            with redirect_stdout(stdout), self.assertRaises(SystemExit) as exit_info:
                github_dork.main()

        self.assertEqual(exit_info.exception.code, 0)
        self.assertEqual(stdout.getvalue().strip(), f'github-dorks {__version__}')

    def test_returns_partial_failure_exit_code(self):
        stats = search_module.ScanStats(failures=1)
        with patch.object(sys, 'argv', ['github-dorks', '-r', 'owner/repo']):
            with patch.object(github_dork, 'create_client', return_value=object()):
                with patch.object(github_dork, 'search', return_value=stats):
                    self.assertEqual(github_dork.main(), 2)

    def test_returns_fatal_exit_code_for_missing_dictionary(self):
        stderr = io.StringIO()
        arguments = [
            'github-dorks', '-r', 'owner/repo', '-d', '/does/not/exist'
        ]
        with patch.object(sys, 'argv', arguments), redirect_stdout(io.StringIO()):
            with patch.object(github_dork, 'create_client', return_value=GitHubClient()):
                with patch('sys.stderr', stderr):
                    self.assertEqual(github_dork.main(), 1)

        self.assertIn('the dorks file path is not valid', stderr.getvalue())


class DorkDictionaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dictionary = Path(__file__).parents[1] / 'github-dorks.txt'
        cls.lines = dictionary.read_text(encoding='utf-8').splitlines()
        cls.dorks = [
            line for line in cls.lines
            if line and not line.startswith(('#', ';'))
        ]

    def test_has_no_duplicate_dorks(self):
        duplicates = sorted({dork for dork in self.dorks if self.dorks.count(dork) > 1})
        self.assertEqual(duplicates, [])

    def test_has_no_surrounding_whitespace(self):
        untrimmed = [line for line in self.lines if line != line.strip()]
        self.assertEqual(untrimmed, [])

    def test_has_balanced_quotes(self):
        malformed = [dork for dork in self.dorks if dork.count('"') % 2]
        self.assertEqual(malformed, [])

    def test_contains_modern_credential_families(self):
        dictionary = '\n'.join(self.dorks)
        for marker in (
            'github_pat_', 'glpat-', 'pypi-', 'OPENAI_API_KEY',
            'ANTHROPIC_API_KEY', 'HF_TOKEN', 'CLOUDFLARE_API_TOKEN',
            'SUPABASE_SERVICE_ROLE_KEY', 'sk_live_',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, dictionary)


if __name__ == '__main__':
    unittest.main()
