"""Command-line interface for github-dorks."""

import argparse
import os
import sys
import time

import feedparser
import github3 as github

from github_dorks import __version__
from github_dorks.dictionaries import available_categories
from github_dorks.search import create_client, search


def monitor(gh_dorks_file=None, feed_token=None, refresh_time=60, categories=None):
    github_user = os.getenv('GH_USER')
    if github_user is None:
        raise ValueError('GH_USER is required for monitoring')

    print('Monitoring merged pull requests for new scans.')
    seen_items = set()
    private_feed = f'https://github.com/{github_user}.private.atom?token={feed_token}'
    while True:
        feed = feedparser.parse(private_feed)
        for item in feed['items']:
            if 'merged pull' in item['title'] and item['title'] not in seen_items:
                search(
                    user_to_search=item['author_detail']['name'],
                    gh_dorks_file=gh_dorks_file,
                    categories=categories,
                )
                seen_items.add(item['title'])
        print('Waiting for new items...')
        time.sleep(refresh_time)


def build_parser():
    parser = argparse.ArgumentParser(
        prog='github-dorks',
        description='Search GitHub for sensitive data patterns',
        epilog='Use responsibly. Only scan repositories you are authorized to assess.',
    )
    parser.add_argument(
        '-v', '--version', action='version', version='%(prog)s ' + __version__
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-u', '--user', dest='user_to_search',
        help='GitHub user/org to search within. Eg: techgaun',
    )
    group.add_argument(
        '-r', '--repo', dest='repo_to_search',
        help='GitHub repo to search within. Eg: techgaun/github-dorks',
    )
    group.add_argument(
        '-m', '--monit', dest='active_monit',
        help='Monitor the GitHub user private feed with this feed token',
    )
    group.add_argument(
        '--list-categories', action='store_true',
        help='List bundled dictionary categories and exit',
    )
    dictionary_group = parser.add_mutually_exclusive_group()
    dictionary_group.add_argument(
        '-d', '--dork', dest='gh_dorks_file',
        help='GitHub dorks file. Eg: github-dorks.txt',
    )
    dictionary_group.add_argument(
        '-c', '--category', action='append', dest='categories',
        choices=available_categories(),
        help='Bundled category to scan; repeat to select multiple',
    )
    parser.add_argument(
        '-o', '--output', '--outputFile', dest='output_filename',
        help='Write results to this file instead of stdout',
    )
    parser.add_argument(
        '--format', choices=('text', 'csv', 'json', 'jsonl'),
        dest='output_format',
        help='Result format (default: text, or CSV when -o is used)',
    )
    parser.add_argument(
        '-f', '--force', action='store_true',
        help='Overwrite an existing output file',
    )
    detail_group = parser.add_mutually_exclusive_group()
    detail_group.add_argument(
        '-q', '--quiet', action='store_true',
        help='Suppress progress and summary messages',
    )
    detail_group.add_argument(
        '--verbose', action='store_true',
        help='Report each query as it runs',
    )
    parser.add_argument(
        '--max-retries', type=int, default=3,
        help='Maximum retries per query for recoverable API failures (default: 3)',
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.list_categories:
        print('\n'.join(available_categories()))
        return 0
    if args.max_retries < 0:
        parser.error('--max-retries must be zero or greater')
    try:
        if args.active_monit:
            monitor(
                args.gh_dorks_file, args.active_monit,
                categories=args.categories,
            )
            return 0
        stats = search(
            repo_to_search=args.repo_to_search,
            user_to_search=args.user_to_search,
            gh_dorks_file=args.gh_dorks_file,
            categories=args.categories,
            output_filename=args.output_filename,
            output_format=args.output_format,
            force=args.force,
            quiet=args.quiet,
            verbose=args.verbose,
            client=create_client(),
            max_retries=args.max_retries,
        )
        return stats.exit_code
    except (OSError, ValueError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    except Exception as error:
        authentication_error = getattr(
            github.exceptions, 'AuthenticationFailed', ()
        )
        if authentication_error and isinstance(error, authentication_error):
            print(f'Error: {error}', file=sys.stderr)
            return 1
        raise
