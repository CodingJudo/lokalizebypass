# Claude Batch Processing Implementation Plan

## Overview

Anthropic's Claude API offers two modes for processing translation requests:

1. **Messages API (Synchronous)** - Immediate results, standard pricing
2. **Message Batches API (Asynchronous)** - Up to 10,000 items, 50% cost savings, 24-hour processing

## Current Implementation Pattern

Our current translation flow:
- Processes batches of 10-20 items synchronously
- Immediate results for each batch
- Suitable for interactive use and small-to-medium volumes

## Claude Batch API Details

### Key Features

- **Cost Savings**: 50% discount on input and output tokens
- **High Throughput**: Up to 10,000 requests per batch
- **Asynchronous Processing**: Completed within 24 hours
- **Batch Size Limit**: Maximum 256 MB total batch size
- **Results Format**: JSONL file with results

### Supported Models

- Claude 3.5 Sonnet
- Claude 3 Opus
- Claude 3 Haiku

### API Endpoints

1. **Create Batch**: `POST /v1/messages/batches`
2. **Check Status**: `GET /v1/messages/batches/{batch_id}`
3. **Retrieve Results**: `GET {results_url}`

### Request Format

```json
{
  "requests": [
    {
      "custom_id": "request-1",
      "params": {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
        "messages": [
          {"role": "user", "content": "Translate..."}
        ]
      }
    }
  ]
}
```

### Response Format

**Batch Creation Response:**
```json
{
  "id": "batch_abc123",
  "processing_status": "validating",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**Batch Status Response:**
```json
{
  "id": "batch_abc123",
  "processing_status": "ended",
  "results_url": "https://api.anthropic.com/v1/messages/batches/batch_abc123/results",
  "created_at": "2024-01-01T00:00:00Z",
  "ended_at": "2024-01-01T12:00:00Z"
}
```

**Results JSONL Format:**
```jsonl
{"custom_id": "request-1", "output": {"content": [{"type": "text", "text": "..."}]}}
{"custom_id": "request-2", "output": {"content": [{"type": "text", "text": "..."}]}}
```

### Processing Status Values

- `validating` - Batch is being validated
- `in_progress` - Batch is being processed
- `finalizing` - Batch is being finalized
- `ended` - Batch processing completed successfully
- `expired` - Batch expired before completion
- `cancelling` - Batch is being cancelled
- `cancelled` - Batch was cancelled

## Implementation Strategy

### Default: Synchronous Messages API

**When to use:**
- Small to medium volumes (< 100 items)
- Immediate results needed
- Interactive use cases

**Implementation:**
- Use standard `POST /v1/messages` endpoint
- Process batches of 10-20 items immediately
- Return results synchronously

### Optional: Asynchronous Batch API

**When to use:**
- Large volumes (100+ items)
- Cost savings are important
- Can wait up to 24 hours for results
- Non-time-sensitive translations

**Implementation:**
- Use `POST /v1/messages/batches` endpoint
- Submit all items in a single batch (up to 10,000)
- Poll batch status until `processing_status == "ended"`
- Retrieve and process results JSONL file
- Map `custom_id` back to original items

## Workflow Comparison

### Synchronous API (Current Pattern)
```
1. Create batch of 10-20 items
2. Send request to /v1/messages
3. Receive immediate response
4. Process results
5. Repeat for next batch
```

### Batch API (New Option)
```
1. Collect all items to translate
2. Create batch request with all items (up to 10,000)
3. Submit to /v1/messages/batches
4. Receive batch_id
5. Poll /v1/messages/batches/{batch_id} until status == "ended"
6. Retrieve results from results_url
7. Process JSONL results file
8. Map custom_id back to original items
```

## Implementation Details

### Provider Interface

The `ClaudeProvider` will support both modes:

```python
class ClaudeProvider(TranslationProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        use_batch_api: bool = False,  # New parameter
        batch_threshold: int = 100,    # Auto-use batch API if items > threshold
        ...
    ):
        ...
    
    def translate_batch(
        self,
        source_lang: str,
        target_lang: str,
        items: List[Dict[str, str]],
        ...
    ) -> Dict[str, Any]:
        # Auto-detect: use batch API if items > batch_threshold
        if len(items) > self.batch_threshold or self.use_batch_api:
            return self._translate_batch_async(items, ...)
        else:
            return self._translate_batch_sync(items, ...)
```

### Batch Status Polling

```python
def _poll_batch_status(self, batch_id: str) -> Dict[str, Any]:
    """Poll batch status until completed."""
    max_wait_time = 24 * 60 * 60  # 24 hours in seconds
    poll_interval = 60  # Poll every 60 seconds
    start_time = time.time()
    
    while True:
        status_response = self._get_batch_status(batch_id)
        status = status_response["processing_status"]
        
        if status == "ended":
            return status_response
        elif status in ["expired", "cancelled"]:
            raise Exception(f"Batch {batch_id} {status}")
        elif time.time() - start_time > max_wait_time:
            raise Exception(f"Batch {batch_id} exceeded max wait time")
        
        time.sleep(poll_interval)
```

### Results Processing

```python
def _process_batch_results(self, results_url: str, items: List[Dict]) -> Dict[str, Any]:
    """Download and process batch results JSONL file."""
    # Download results
    response = requests.get(results_url, headers=self._get_headers())
    results = response.json()
    
    # Create mapping: custom_id -> item
    item_map = {item["custom_id"]: item for item in items}
    
    # Process results
    translations = []
    for result in results:
        custom_id = result["custom_id"]
        output = result["output"]
        content = output["content"][0]["text"]
        
        # Extract JSON from content
        json_text = self._extract_json(content)
        # ... validate and process ...
        
        translations.append(...)
    
    return {"targetLanguage": target_lang, "translations": translations}
```

## CLI Integration

### New Flags

```bash
# Use batch API explicitly
python -m src.cli run \
  --target-lang fr \
  --provider claude \
  --use-batch-api

# Auto-detect (use batch API if >100 items)
python -m src.cli run \
  --target-lang fr \
  --provider claude \
  --batch-threshold 100

# Synchronous (default, immediate results)
python -m src.cli run \
  --target-lang fr \
  --provider claude
```

## Cost Comparison

### Example: 1,000 translation items

**Synchronous API:**
- Cost: 1,000 requests × standard pricing
- Time: ~10-30 minutes (depending on batch size)
- Results: Immediate

**Batch API:**
- Cost: 1,000 requests × 50% discount = **50% savings**
- Time: Up to 24 hours
- Results: Asynchronous

## Recommendations

1. **Default to synchronous API** for immediate results
2. **Auto-detect batch API** when items > threshold (default: 100)
3. **Allow explicit override** with `--use-batch-api` flag
4. **Store batch_id** for resumability (if batch processing is interrupted)
5. **Document trade-offs** clearly (speed vs. cost)

## Testing Strategy

### Synchronous API Tests
- Standard unit tests (similar to OpenAIProvider)
- Mock HTTP requests
- Test error handling

### Batch API Tests
- Test batch creation
- Test status polling
- Test results retrieval
- Test JSONL parsing
- Test custom_id mapping
- Test error cases (expired, cancelled batches)
- Test resumability (storing/loading batch_id)

## References

- [Anthropic Message Batches API](https://www.anthropic.com/news/message-batches-api)
- [Creating Message Batches Documentation](https://docs.anthropic.com/en/api/creating-message-batches)
- [Messages API Documentation](https://docs.anthropic.com/en/api/messages)

