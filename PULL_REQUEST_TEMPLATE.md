### Please include all of the following fields when adding dorks/patterns
- Search URL: https://github.com/search?q=<SOMETHING_HERE>
- Number of search results at time of PR: 
- Impact of data disclosed (see table below): 
- Description of data disclosed: 

| Icon/Name | Description                                                                                             | Examples                                                       |
|-----------|---------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
❓ Unknown    | The impact of this data is highly variable or unknown)                                                 | N/A                                                                |
➖ Low      | This data will provide minimal access or mostly public information)                                     | Non-stored XSS, Limited scope + read-only API access           |
➕ Moderate | This data will provide some access or information                                                       | Stored XSS in some cases, read-only or limited write API access|
⚠️ High     | This data will provide single-user access or secret information)                                        | Usernames/passwords, OAuth tokens                              |
❗️ Critical   | This data will provide complete control, access to several users, or confidential/personal information | Credential database dumps, AWS keys
