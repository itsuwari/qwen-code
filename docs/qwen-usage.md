# Qwen Usage Accounting

Qwen reports usage with every API response. The `usage` field contains the token counts for the request and the model's reply:

```json
{
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 30,
    "total_tokens": 45
  }
}
```

Both the prompt and the completion tokens contribute to your interaction quota. Each API call counts once regardless of response size.

## Reducing Interaction Costs
- **Trim prompts** – remove unnecessary context before sending a request.
- **Set `max_tokens`** – cap the length of model outputs to avoid large completions.
- **Batch messages** – combine related questions into a single request when possible.
- **Reuse conversations** – carry forward previous responses instead of repeating information.

Monitoring these counts helps avoid wasting interactions and keeps usage within the allotted limits.
