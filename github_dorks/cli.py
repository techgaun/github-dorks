import github3 as github
import os
import argparse
import csv
import time
import feedparser
from copy import copy
from contextlib import nullcontext
from sys import stderr, prefix

from github_dorks import __version__

gh_user = os.getenv('GH_USER', None)
gh_pass = os.getenv('GH_PWD', None)
gh_token = os.getenv('GH_TOKEN', None)
gh_url = os.getenv('GH_URL', None)

if gh_url is None:
    gh = github.GitHub(username=gh_user, password=gh_pass, token=gh_token)
else:
    gh = github.GitHubEnterprise(
        url=gh_url, username=gh_user, password=gh_pass, token=gh_token)


def search_wrapper(gen):
    while True:
        gen_back = copy(gen)
        try:
            yield next(gen)
        except StopIteration:
            return
        except github.exceptions.ForbiddenError:
            search_rate_limit = gh.rate_limit()['resources']['search']
            # limit_remaining = search_rate_limit['remaining']
            reset_time = search_rate_limit['reset']
            current_time = int(time.time())
            sleep_time = reset_time - current_time + 1
            stderr.write(
                'GitHub Search API rate limit reached. Sleeping for %d seconds.\n\n'
                % (sleep_time))
            time.sleep(sleep_time)
            yield next(gen_back)
        except Exception as e:
            raise e


def metasearch(repo_to_search=None,
               user_to_search=None,
               gh_dorks_file=None,
               active_monit=None,
               output_filename=None,
               refresh_time=60):
    if active_monit is None:
        search(repo_to_search, user_to_search, gh_dorks_file, active_monit, output_filename)
    else:
        monit(gh_dorks_file, active_monit, refresh_time)


def monit(gh_dorks_file=None, active_monit=None, refresh_time=60):
    if gh_user is None:
        raise Exception('Error, env Github user variable needed')
    else:
        print(
            'Monitoring user private feed searching new code to be dorked.' +
            'Every new merged pull request trigger user scan.'
        )
        print('-----')
        items_history = list()
        gh_private_feed = "https://github.com/{}.private.atom?token={}".format(
            gh_user, active_monit)
        while True:
            feed = feedparser.parse(gh_private_feed)
            for i in feed['items']:
                if 'merged pull' in i['title']:
                    if i['title'] not in items_history:
                        search(
                            user_to_search=i['author_detail']['name'],
                            gh_dorks_file=gh_dorks_file)
                        items_history.append(i['title'])
            print('Waiting for new items...')
            time.sleep(refresh_time)


def search(repo_to_search=None,
           user_to_search=None,
           gh_dorks_file=None,
           active_monit=None,
           output_filename=None):

    if gh_dorks_file is None:
        for path_prefix in ['.', os.path.join(prefix, 'github-dorks/')]:
            filename = os.path.join(path_prefix, 'github-dorks.txt')
            if os.path.isfile(filename):
                gh_dorks_file = filename
                break

    if gh_dorks_file is None or not os.path.isfile(gh_dorks_file):
        raise Exception('Error, the dorks file path is not valid')
    if user_to_search:
        print("Scanning User: ", user_to_search)
    if repo_to_search:
        print("Scanning Repo: ", repo_to_search)
    found = False

    output_context = (
        open(output_filename, 'w', newline='', encoding='utf-8')
        if output_filename else nullcontext(None)
    )

    with open(gh_dorks_file, 'r', encoding='utf-8') as dork_file, output_context as output_file:
        # Write CSV Header
        csv_writer = None
        if output_file:
            csv_writer = csv.writer(output_file)
            csv_writer.writerow([
                'Issue Type (Dork)', 'Text Matches', 'File Path',
                'Score/Relevance', 'URL of File'
            ])
        for dork in dork_file:
            dork = dork.strip()
            if not dork or dork[0] in '#;':
                continue
            addendum = ''
            if repo_to_search:
                addendum = ' repo:' + repo_to_search
            elif user_to_search:
                addendum = ' user:' + user_to_search

            dork = dork + addendum
            search_results = search_wrapper(gh.search_code(dork))
            try:
                for search_result in search_results:
                    found = True
                    fmt_args = {
                        'dork': dork,
                        'text_matches': search_result.text_matches,
                        'path': search_result.path,
                        'score': search_result.score,
                        'url': search_result.html_url
                    }

                    # Either write to file or print output
                    if csv_writer:
                        csv_writer.writerow([
                            fmt_args['dork'], fmt_args['text_matches'],
                            fmt_args['path'], fmt_args['score'], fmt_args['url']
                        ])
                    else:
                        result = '\n'.join([
                            'Found result for {dork}',
                            'Text matches: {text_matches}', 'File path: {path}',
                            'Score/Relevance: {score}', 'URL of File: {url}', ''
                        ]).format(**fmt_args)
                        print(result)

            except github.exceptions.GitHubError as e:
                print('GitHubError encountered on search of dork: ' + dork)
                print(e)
                return
            except Exception as e:
                print(e)
                print('Error encountered on search of dork: ' + dork)

    if not found:
        print('No results for your dork search' + addendum + '. Hurray!')


def main():
    parser = argparse.ArgumentParser(
        prog='github-dorks',
        description='Search GitHub for sensitive data patterns',
        epilog='Use responsibly. Only scan repositories you are authorized to assess.')

    parser.add_argument(
        '-v', '--version', action='version', version='%(prog)s ' + __version__)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-u',
        '--user',
        dest='user_to_search',
        action='store',
        help='GitHub user/org to search within. Eg: techgaun')

    group.add_argument(
        '-r',
        '--repo',
        dest='repo_to_search',
        action='store',
        help='GitHub repo to search within. Eg: techgaun/github-dorks')

    parser.add_argument(
        '-d',
        '--dork',
        dest='gh_dorks_file',
        action='store',
        help='GitHub dorks file. Eg: github-dorks.txt')

    group.add_argument(
        '-m',
        '--monit',
        dest='active_monit',
        action='store',
        help='Monitors GitHub user private feed with feed token'
    )

    parser.add_argument(
        '-o',
        '--outputFile',
        dest='output_filename',
        action='store',
        help='CSV File to write results to. This overwrites the file provided! Eg: out.csv'
    )

    args = parser.parse_args()
    metasearch(
        repo_to_search=args.repo_to_search,
        user_to_search=args.user_to_search,
        gh_dorks_file=args.gh_dorks_file,
        active_monit=args.active_monit,
        output_filename=args.output_filename)


if __name__ == '__main__':
    main()
