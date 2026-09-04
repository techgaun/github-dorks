import csv
import io
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


fake_github3 = types.ModuleType('github3')
fake_github3.GitHub = lambda **kwargs: None
fake_github3.GitHubEnterprise = lambda **kwargs: None
fake_github3.exceptions = types.SimpleNamespace(
    ForbiddenError=FakeForbiddenError,
    GitHubError=FakeGitHubError,
)
sys.modules.setdefault('github3', fake_github3)
sys.modules.setdefault('feedparser', types.ModuleType('feedparser'))

from github_dorks import __version__, cli as github_dork  # noqa: E402


class SearchResult:
    text_matches = ['secret, with comma']
    path = 'config/file.env'
    score = 42
    html_url = 'https://github.example/result'


class GitHubClient:
    def search_code(self, query):
        self.query = query
        return iter([SearchResult()])


class SearchTests(unittest.TestCase):
    def test_writes_valid_csv_and_scopes_query_to_repository(self):
        client = GitHubClient()
        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            output = Path(directory) / 'results.csv'
            dorks.write_text('# comment\nfilename:.env PASSWORD\n', encoding='utf-8')

            with patch.object(github_dork, 'gh', client):
                github_dork.search(
                    repo_to_search='owner/repo',
                    gh_dorks_file=str(dorks),
                    output_filename=str(output),
                )

            with output.open(newline='', encoding='utf-8') as output_file:
                rows = list(csv.reader(output_file))

        self.assertEqual(client.query, 'filename:.env PASSWORD repo:owner/repo')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], client.query)
        self.assertEqual(rows[1][1], "['secret, with comma']")

    def test_reports_when_no_results_are_found(self):
        client = GitHubClient()
        client.search_code = lambda query: iter([])
        with tempfile.TemporaryDirectory() as directory:
            dorks = Path(directory) / 'dorks.txt'
            dorks.write_text('filename:.env\n', encoding='utf-8')
            stdout = io.StringIO()
            with patch.object(github_dork, 'gh', client), redirect_stdout(stdout):
                github_dork.search(
                    user_to_search='example', gh_dorks_file=str(dorks)
                )

        self.assertIn('No results for your dork search user:example', stdout.getvalue())

    def test_rejects_missing_dorks_file_with_clear_error(self):
        with self.assertRaisesRegex(Exception, 'dorks file path is not valid'):
            github_dork.search(gh_dorks_file='/does/not/exist')


class CommandLineTests(unittest.TestCase):
    def test_version_comes_from_package_metadata(self):
        stdout = io.StringIO()
        with patch.object(sys, 'argv', ['github-dorks', '--version']):
            with redirect_stdout(stdout), self.assertRaises(SystemExit) as exit_info:
                github_dork.main()

        self.assertEqual(exit_info.exception.code, 0)
        self.assertEqual(stdout.getvalue().strip(), f'github-dorks {__version__}')


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
