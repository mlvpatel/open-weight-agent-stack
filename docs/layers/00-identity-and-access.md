# Layer 0: Identity and access

> Who is acting, on whose behalf, with how much authority. Ring: harness. Manual: [section 18](../../MANUAL.md#18-identity-delegation-and-authority), [section 19](../../MANUAL.md#19-threat-model).

## What this layer does

Every request that enters the stack carries an identity, and every downstream component enforces a scope derived from it: the retrieval filter, the cache key, the tool allow-list, the spend budget. The agent is its own principal. It acts with delegated, attenuated authority, never with the user's raw credentials, so an agent can always do less than the human who asked.

Passwords belong to the identity provider, not to this stack. The stack consumes tokens.

## How to choose

- Already have an IdP (Okta, Entra, Google Workspace): federate with OIDC and skip new infrastructure.
- Self-hosting everything: Keycloak is the default open IdP; heavyweight but complete.
- Service-to-service identity at scale: SPIFFE/SPIRE issues workload identities so services authenticate without shared secrets.
- Policy decisions beyond role checks: OPA (Rego) or Cedar evaluate who-can-do-what as versioned policy code.

## The options

| Tool | Best for | Link |
|---|---|---|
| OIDC / OAuth2 | The protocol floor every option below speaks | [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html) |
| Token exchange (RFC 8693) | Attenuating a user token into a narrower agent token | [RFC 8693](https://www.rfc-editor.org/rfc/rfc8693) |
| Keycloak | Self-hosted IdP, SSO, token exchange | [keycloak.org](https://www.keycloak.org/) |
| Auth0 | Managed IdP when operating one is not your business | [auth0.com](https://auth0.com/) |
| SPIFFE / SPIRE | Workload identity, mTLS everywhere | [spiffe.io](https://spiffe.io/) |
| OPA | Policy as code, Rego | [openpolicyagent.org](https://www.openpolicyagent.org/) |
| Cedar | Policy as code, typed and verifiable | [cedar-policy](https://github.com/cedar-policy/cedar) |

## Wiring it in

The gateway validates the token once (issuer, audience, expiry, scope) and stamps an internal context object that travels with the request. Components trust the stamp, not the raw token. Tool calls that write carry the acting identity for the audit trail: user to agent to tool. The threat model rows ASI03 and ASI09 in [section 19](../../MANUAL.md#19-threat-model) assume this layer exists; without it they have no control to point at.

## Deep-dive links

[OAuth 2.0 Token Exchange](https://www.rfc-editor.org/rfc/rfc8693) · [OWASP Agentic Top 10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) · [SPIFFE concepts](https://spiffe.io/)
