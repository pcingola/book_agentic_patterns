# FastMCP Documentation

Split from the original `fastmcp.llms-full.md` (now in `docs/original/`).

## Getting Started

- [Welcome to FastMCP 3.0](fastmcp/29_welcome_to_fastmcp_3_0.md)
- [Installation](fastmcp/27_installation.md)
- [Quickstart](fastmcp/28_quickstart.md)
- [Upgrade Guide](fastmcp/26_upgrade_guide.md)
- [Changelog](fastmcp/01_changelog.md)
- [FastMCP Updates](fastmcp/103_fastmcp_updates.md)

## Server

- [The FastMCP Server](fastmcp/91_the_fastmcp_server.md)
- [Running Your Server](fastmcp/21_running_your_server.md)
- [Tools](fastmcp/95_tools.md)
- [Prompts](fastmcp/81_prompts.md)
- [Resources & Templates](fastmcp/89_resources_templates.md)
- [MCP Context](fastmcp/72_mcp_context.md)
- [Dependency Injection](fastmcp/73_dependency_injection.md)
- [User Elicitation](fastmcp/74_user_elicitation.md)
- [Lifespans](fastmcp/76_lifespans.md)
- [Icons](fastmcp/75_icons.md)
- [Middleware](fastmcp/78_middleware.md)
- [Pagination](fastmcp/79_pagination.md)
- [Progress Reporting](fastmcp/80_progress_reporting.md)
- [Sampling](fastmcp/90_sampling.md)
- [Background Tasks](fastmcp/93_background_tasks.md)
- [Authorization](fastmcp/71_authorization.md)
- [Versioning](fastmcp/101_versioning.md)
- [Component Visibility](fastmcp/102_component_visibility.md)
- [Storage Backends](fastmcp/92_storage_backends.md)

## Authentication

- [Authentication](fastmcp/65_authentication.md)
- [Bearer Token Authentication](fastmcp/02_bearer_token_authentication.md)
- [CIMD Authentication](fastmcp/03_cimd_authentication.md)
- [OAuth Authentication](fastmcp/04_oauth_authentication.md)
- [Full OAuth Server](fastmcp/66_full_oauth_server.md)
- [OAuth Proxy](fastmcp/67_oauth_proxy.md)
- [OIDC Proxy](fastmcp/68_oidc_proxy.md)
- [Remote OAuth](fastmcp/69_remote_oauth.md)
- [Token Verification](fastmcp/70_token_verification.md)

## Client

- [The FastMCP Client](fastmcp/06_the_fastmcp_client.md)
- [Client CLI](fastmcp/05_client_cli.md)
- [Calling Tools](fastmcp/17_calling_tools.md)
- [Getting Prompts](fastmcp/12_getting_prompts.md)
- [Reading Resources](fastmcp/13_reading_resources.md)
- [Client Roots](fastmcp/14_client_roots.md)
- [User Elicitation](fastmcp/07_user_elicitation.md)
- [LLM Sampling](fastmcp/15_llm_sampling.md)
- [Background Tasks](fastmcp/16_background_tasks.md)
- [Notifications](fastmcp/10_notifications.md)
- [Progress Monitoring](fastmcp/11_progress_monitoring.md)
- [Server Logging](fastmcp/09_server_logging.md)
- [Client Logging](fastmcp/77_client_logging.md)
- [Client Transports](fastmcp/18_client_transports.md)

## Providers

- [Providers](fastmcp/86_providers.md)
- [Local Provider](fastmcp/84_local_provider.md)
- [Filesystem Provider](fastmcp/83_filesystem_provider.md)
- [MCP Proxy Provider](fastmcp/87_mcp_proxy_provider.md)
- [Custom Providers](fastmcp/82_custom_providers.md)
- [Mounting Servers](fastmcp/85_mounting_servers.md)
- [Skills Provider](fastmcp/88_skills_provider.md)

## Transforms

- [Transforms Overview](fastmcp/100_transforms_overview.md)
- [Namespace Transform](fastmcp/96_namespace_transform.md)
- [Prompts as Tools](fastmcp/97_prompts_as_tools.md)
- [Resources as Tools](fastmcp/98_resources_as_tools.md)
- [Tool Transformation](fastmcp/99_tool_transformation.md)

## Deployment

- [HTTP Deployment](fastmcp/19_http_deployment.md)
- [Prefect Horizon](fastmcp/20_prefect_horizon.md)
- [Project Configuration](fastmcp/22_project_configuration.md)
- [OpenTelemetry](fastmcp/94_opentelemetry.md)

## Integrations

- [Anthropic API](fastmcp/30_anthropic_api_fastmcp.md)
- [Auth0 OAuth](fastmcp/31_auth0_oauth_fastmcp.md)
- [AuthKit](fastmcp/32_authkit_fastmcp.md)
- [AWS Cognito OAuth](fastmcp/33_aws_cognito_oauth_fastmcp.md)
- [Azure (Microsoft Entra ID) OAuth](fastmcp/34_azure_microsoft_entra_id_oauth_fastmcp.md)
- [ChatGPT](fastmcp/35_chatgpt_fastmcp.md)
- [Claude Code](fastmcp/36_claude_code_fastmcp.md)
- [Claude Desktop](fastmcp/37_claude_desktop_fastmcp.md)
- [Cursor](fastmcp/38_cursor_fastmcp.md)
- [Descope](fastmcp/39_descope_fastmcp.md)
- [Discord OAuth](fastmcp/40_discord_oauth_fastmcp.md)
- [Eunomia Authorization](fastmcp/41_eunomia_authorization_fastmcp.md)
- [FastAPI](fastmcp/42_fastapi_fastmcp.md)
- [Gemini SDK](fastmcp/43_gemini_sdk_fastmcp.md)
- [Gemini CLI](fastmcp/44_gemini_cli_fastmcp.md)
- [GitHub OAuth](fastmcp/45_github_oauth_fastmcp.md)
- [Google OAuth](fastmcp/46_google_oauth_fastmcp.md)
- [Goose](fastmcp/47_goose_fastmcp.md)
- [MCP JSON Configuration](fastmcp/48_mcp_json_configuration_fastmcp.md)
- [OCI IAM OAuth](fastmcp/49_oci_iam_oauth_fastmcp.md)
- [OpenAI API](fastmcp/50_openai_api_fastmcp.md)
- [OpenAPI](fastmcp/51_openapi_fastmcp.md)
- [Permit.io Authorization](fastmcp/52_permit_io_authorization_fastmcp.md)
- [Scalekit](fastmcp/53_scalekit_fastmcp.md)
- [Supabase](fastmcp/54_supabase_fastmcp.md)
- [WorkOS](fastmcp/55_workos_fastmcp.md)

## CLI & Testing

- [FastMCP CLI](fastmcp/56_fastmcp_cli.md)
- [Generate CLI](fastmcp/08_generate_cli.md)
- [Testing your FastMCP Server](fastmcp/58_testing_your_fastmcp_server.md)
- [Contrib Modules](fastmcp/57_contrib_modules.md)

## API Reference

- [Decorators](fastmcp/59_decorators.md)
- [fastmcp.decorators](fastmcp/60_fastmcp_decorators.md)
- [Dependencies](fastmcp/61_dependencies.md)
- [fastmcp.dependencies](fastmcp/62_fastmcp_dependencies.md)
- [Exceptions](fastmcp/63_exceptions.md)
- [fastmcp.exceptions](fastmcp/64_fastmcp_exceptions.md)

## Development

- [Contributing](fastmcp/23_contributing.md)
- [Releases](fastmcp/24_releases.md)
- [Tests](fastmcp/25_tests.md)
