import requests
import os
import subprocess
import unittest2 as unittest

from subprocess import Popen


class SecretsTest(unittest.TestCase):


    def test_secrets_in_repos(self):
        org_name = os.getenv("orgname")
        params = {'type': 'all', 'per_page': '200'}
        url = 'https://api.github.com/orgs/'+str(org_name)+'/repos'
        resp = requests.get(url=url, params=params)
        for repo in resp.json():
            yield self.check_secrets_in_a_repo, (repo, )

    def check_secrets_in_a_repo(self, repo):
        dork_resp = Popen(
            ['python', 'github-dork.py', '-r', repo['full_name']],
            stdout=subprocess.PIPE)
        output, err = dork_resp.communicate()
        self.assertTrue('Hurray' in output, output)
        print output

if __name__ == '__main__':
    SecretsTest().run()
