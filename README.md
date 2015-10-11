# Github Dorks
[Github search](https://github.com/search) is quite powerful and useful feature and can be used to search sensitive data on the repositories. Collection of github dorks that can reveal sensitive personal and/or organizational information such as private keys, credentials, authentication tokens, etc. This list is supposed to be useful for assessing security and performing pen-testing of systems.

### Contribution
Please consider contributing the dorks that can reveal potentially senstive information in github.

### List of Dorks
List of dorks follow. I am not categorizing at the moment. Instead am going to just the list of dorks with optionally a description separated by # in the same line. Many of the dorks can be modified to make the search more specific or generic. You can see more options [HERE](https://github.com/search#search_cheatsheet_pane).

```
filename:.npmrc _auth # npm registry authentication data

filename:.dockercfg auth  # docker registry authentication data

extension:pem private # private keys

extension:ppk private # puttygen private keys

filename:id_rsa or filename:id_dsa  # private ssh keys

extension:sql mysql dump  # mysql dump

extension:sql mysql dump password # mysql dump look for password; you can try varieties

filename:credentials aws_access_key_id  # might return false negatives with dummy values

filename:.s3cfg # might return false negatives with dummy values

filename:wp-config.php  # wordpress config files

filename:.htpasswd  # htpasswd files

filename:.env DB_USERNAME NOT homestead # laravel .env (CI, various ruby based frameworks too)

filename:.env MAIL_HOST=smtp.gmail.com  # gmail smtp configuration (try different smtp services too)

filename:.git-credentials # git credentials store, add NOT username for more valid results

PT_TOKEN language:bash  # pivotaltracker tokens

filename:.bashrc password # search for passwords, etc. in .bashrc (try with .bash_profile too)

filename:.bashrc mailchimp  # variation of above (try more variations)

filename:.bash_profile aws  # aws access and secret keys

rds.amazonaws.com password  # Amazon RDS possible credentials

extension:json api.forecast.io  # try variations, find api keys/secrets

extension:json mongolab.com # mongolab credentials in json configs

extension:yaml mongolab.com # mongolab credentials in yaml configs (try with yml)

jsforce extension:js conn.login # possible salesforce credentials in nodejs projects

SF_USERNAME "salesforce"  # possible salesforce credentials
```
