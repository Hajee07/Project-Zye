# ZYE AI — DAY 27: INFRASTRUCTURE SECURITY & PRIVACY ENFORCEMENT

## 1. Security Architecture Summary
Day 27 implements defense-in-depth security around all external routing and resilience operations:
1. **Local-Only Air-Gapped Mode (`LOCAL_ONLY`):** Strictly enforces offline execution on `http://127.0.0.1:11434`. Structural blocks prevent any cloud provider from receiving data.
2. **SSRF Validator Integration:** Validates all custom endpoints to prevent server-side request forgery into private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, AWS metadata `169.254.169.254`).
3. **Outbound Prompt Sanitization:** Redacts detected API keys and credentials before outbound HTTP dispatch.
4. **Secret Masking:** Exposes only masked credentials (`sk-ant...`) in diagnostics and metadata tools.
5. **No Dangerous Administrative MCP Tools:** Reset tools (`reset_provider_health`) are safe operational resets for circuit breakers, with zero destructive shell capabilities.
