# Reference Implementation

Client/server implementation in TypeScript: [feat/url-elicitation](https://github.com/modelcontextprotocol/typescript-sdk/compare/main...ArcadeAI:mcp-typescript-sdk:feat/url-elicitation)

Explainer video: [https://drive.google.com/file/d/1llCFS9wmkK\_RUgi5B-zHfUUgy-CNb0n0/view?usp=sharing](https://drive.google.com/file/d/1llCFS9wmkK_RUgi5B-zHfUUgy-CNb0n0/view?usp=sharing)

## Security Implications

This SEP introduces several security considerations:

### URL Security Requirements

1. **SSRF Prevention**: Clients must validate URLs to prevent Server-Side Request Forgery attacks
2. **Protocol Restrictions**: Only HTTPS URLs are allowed for URL elicitation
3. **Domain Validation**: Clients must clearly display target domains to users

### Trust Boundaries

URL elicitation explicitly creates clear trust boundaries:

* The MCP client never sees sensitive data obtained by the MCP server via URL elicitation
* The MCP server must independently verify user identity
* Third-party services interact directly with users through secure browser contexts

### Identity Verification

Servers must verify that the user completing a URL elicitation is the same user who initiated the request. Verifying the identity of the user must not rely on untrusted input (e.g. user input) from the client.

### Implementation Requirements

1. **Clients must**:
   * Use secure browser contexts that prevent inspection of user inputs
   * Validate URLs for SSRF protection
   * Obtain explicit user consent before opening URLs
   * Clearly display target domains

2. **Servers must**:
   * Bind elicitation state to authenticated user sessions
   * Verify user identity at the beginning and end of a URL elicitation flow
   * Implement appropriate rate limiting

3. **Both parties should**:
   * Log security events for audit purposes
   * Implement timeout mechanisms for elicitation requests
   * Provide clear error messages for security failures

### Relationship to Existing Security Measures

This proposal builds upon and complements existing MCP security measures:

* Works within the existing MCP authorization framework (MCP authorization is not affected by this proposal)
* Follows Security Best Practices regarding token handling
* Maintains separation of concerns between client-server and server-third-party authorization
