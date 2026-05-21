# mozilla-ai-tests

> Tests of Mozilla libs (any-llm, any-agent, ...)


## Exploring...

* First, configuration with a `.env` file:
```bash
# Model providers (comma-separated list of providers)
PROVIDERS=ollama,anthropic

# Provider and model to use by default
DEFAULT_MODEL=ollama/ministral-3:3b

# Ollama configuration (if not localhost)
OLLAMA_HOST="http://example.com:11434"

# Provider keys
ANTHROPIC_API_KEY="sk-ant-..."
```

* [exploring-any-llm.py](exploring-any-llm.py): how to use [any-llm](https://github.com/mozilla-ai/any-llm), the same code for any LLM providers, that's great !


## TODO

* Translate into english (désolé...)
