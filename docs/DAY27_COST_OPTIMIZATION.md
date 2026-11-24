# ZYE AI — DAY 27: COST-AWARE ROUTING & PRICING RATE CARDS

## 1. Cost Optimization Objectives
To prevent unexpected commercial API bills while maintaining high model performance:
- Maintain an accurate, configurable pricing rate card across supported models.
- Provide pre-execution request cost estimation.
- Track post-execution billable costs using returned usage metadata.
- Prioritize free local inference (Ollama) or economical models for routine tasks.

---

## 2. Official Pricing Rate Card
Prices configured per 1,000,000 tokens (USD):

```
+------------------------------------+------------------+-------------------+
| Model                              | Input Price / 1M | Output Price / 1M |
+------------------------------------+------------------+-------------------+
| Local Ollama (llama3.2, deepseek)  | $0.00 (Free)     | $0.00 (Free)      |
| DeepSeek Chat (deepseek-chat)      | $0.14            | $0.28             |
| OpenAI GPT-4o-mini                 | $0.15            | $0.60             |
| Anthropic Claude-3-Haiku           | $0.25            | $1.25             |
| Groq Cloud (llama-3.3-70b)         | $0.59            | $0.79             |
| OpenAI GPT-4o                      | $2.50            | $10.00            |
| Anthropic Claude-3.5-Sonnet        | $3.00            | $15.00            |
| Perplexity Sonar-Pro               | $3.00            | $15.00            |
+------------------------------------+------------------+-------------------+
```

---

## 3. Strict Truth in Cost Reporting
> [!IMPORTANT]
> - If an unknown custom model is queried, the estimator reports `cost_status: "UNKNOWN"` and `estimated_cost_usd: null`.
> - Zye AI **never fabricates pricing or claims unverified cost savings**.
> - Cost optimization **never overrides privacy, safety, or explicit user provider selection**.

---

## 4. MCP Tools Exposing Cost Data
- `get_provider_cost_estimate(provider_name, model_name, input_tokens, output_tokens)`: Returns itemized USD estimate.
- `get_provider_usage_report()`: Generates aggregated cost accounting summary and compares current rate cards.
