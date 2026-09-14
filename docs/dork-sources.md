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
- [Groq API keys](https://console.groq.com/docs/quickstart)
- [Mistral API authentication](https://docs.mistral.ai/api/)
- [Cohere API keys](https://docs.cohere.com/docs/rate-limits)
- [Replicate API tokens](https://replicate.com/docs/topics/security/api-tokens)
- [Pinecone API keys](https://docs.pinecone.io/guides/get-started/authentication)
- [LangSmith environment variables](https://docs.langchain.com/langsmith/observability-quickstart)

## Identity and secrets management

- [1Password service account tokens](https://developer.1password.com/docs/service-accounts/use-with-1password-cli/)
- [Vault token environment variable](https://developer.hashicorp.com/vault/docs/commands#environment-variables)
- [Doppler service tokens](https://docs.doppler.com/docs/service-tokens)
- [Infisical machine identities](https://infisical.com/docs/documentation/platform/identities/machine-identities)
- [Auth0 application credentials](https://auth0.com/docs/get-started/applications/application-settings)
- [Clerk environment variables](https://clerk.com/docs/guides/development/clerk-environment-variables)

## Databases and data platforms

- [Neon API authentication](https://api-docs.neon.tech/reference/authentication)
- [PlanetScale service tokens](https://planetscale.com/docs/concepts/service-tokens)
- [Upstash Redis REST API](https://upstash.com/docs/redis/features/restapi)
- [Upstash Vector REST API](https://upstash.com/docs/vector/api/get-started)
- [MongoDB Atlas API authentication](https://www.mongodb.com/docs/atlas/configure-api-access/)
- [Databricks personal access tokens](https://docs.databricks.com/aws/en/dev-tools/auth/pat)

## Observability and developer security

- [New Relic API keys](https://docs.newrelic.com/docs/apis/intro-apis/new-relic-api-keys/)
- [Grafana service account tokens](https://grafana.com/docs/grafana/latest/administration/service-accounts/)
- [Honeycomb API keys](https://docs.honeycomb.io/configure/environments/manage-api-keys/)
- [PagerDuty API access keys](https://developer.pagerduty.com/docs/rest-api-v2/authentication/)
- [Snyk authentication](https://docs.snyk.io/snyk-cli/authenticate-to-use-the-cli)

## Cloud and infrastructure

- [HCP Terraform CLI credentials](https://developer.hashicorp.com/terraform/cli/config/config-file#credentials)
- [Cloudflare API tokens](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)
- [DigitalOcean API tokens](https://docs.digitalocean.com/reference/api/create-personal-access-token/)
- [Pulumi access tokens](https://www.pulumi.com/docs/administration/access-identity/access-tokens/)
- [Vercel access tokens](https://vercel.com/docs/rest-api/reference/welcome#creating-an-access-token)
- [Supabase environment variables](https://supabase.com/docs/guides/functions/secrets)
- [Sentry authentication tokens](https://docs.sentry.io/api/auth/)
- [Netlify access tokens](https://docs.netlify.com/api-and-cli-guides/api-guides/get-started-with-api/)
- [Fly.io access tokens](https://fly.io/docs/security/tokens/)
- [Firebase CLI authentication](https://firebase.google.com/docs/cli#cli-ci-systems)

## General secret formats

- [GitHub-supported secret patterns](https://docs.github.com/en/code-security/reference/secret-security/supported-secret-scanning-patterns)
