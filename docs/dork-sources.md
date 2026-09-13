# Dork source references

The dictionaries in `github_dorks/dorks/` favor documented token prefixes and
canonical environment-variable names. The generated `github-dorks.txt`
aggregate contains every category for backward compatibility. Prefixes
generally produce stronger signals; variable-name searches also catch providers
that do not guarantee a stable public token format.

These references support the modern credential families added to the
dictionary. They are not exhaustive, and a match still requires manual review.

## Git hosting and package registries

- [GitHub token formats](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)
- [GitLab token prefixes](https://docs.gitlab.com/security/tokens/#token-prefixes)
- [npm access tokens](https://docs.npmjs.com/about-access-tokens/)
- [PyPI token format](https://docs.pypi.org/trusted-publishers/internals/)

## AI providers

- [OpenAI API key setup](https://platform.openai.com/docs/quickstart)
- [Claude API authentication](https://platform.claude.com/docs/en/api/overview#authentication)
- [Hugging Face user access tokens](https://huggingface.co/docs/hub/security-tokens)

## Cloud and infrastructure

- [HCP Terraform CLI credentials](https://developer.hashicorp.com/terraform/cli/config/config-file#credentials)
- [Cloudflare API tokens](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)
- [DigitalOcean API tokens](https://docs.digitalocean.com/reference/api/create-personal-access-token/)
- [Pulumi access tokens](https://www.pulumi.com/docs/administration/access-identity/access-tokens/)
- [Vercel access tokens](https://vercel.com/docs/rest-api/reference/welcome#creating-an-access-token)
- [Supabase environment variables](https://supabase.com/docs/guides/functions/secrets)
- [Sentry authentication tokens](https://docs.sentry.io/api/auth/)

## General secret formats

- [GitHub-supported secret patterns](https://docs.github.com/en/code-security/reference/secret-security/supported-secret-scanning-patterns)
