# AI Integration Framework

This package provides a modular AI integration framework for the Inbox Zen Email Parsing MCP Server, supporting multiple AI providers through a common interface.

## Architecture

```
src/ai/
├── __init__.py           # Package exports and registry initialization
├── base/                 # Abstract base classes and interfaces
│   ├── __init__.py
│   ├── ai_interface.py   # AIInterface abstract base class
│   └── ai_plugin.py      # AIPlugin abstract base class
├── providers/            # Provider implementations
│   ├── __init__.py
│   └── sambanova/        # SambaNova provider implementation
└── registry.py          # Plugin registry and management
```

## Key Components

### AIInterface

Abstract base class defining the interface that all AI providers must implement. Key methods include:

- `analyze_email()`: Analyze an email and extract structured information
- `extract_tasks()`: Extract tasks from text
- `analyze_sentiment()`: Analyze sentiment of text
- `analyze_thread()`: Analyze a thread of messages

### AIPlugin

Base class for AI provider plugins. Handles:

- Plugin initialization and configuration
- Provider registration
- Lifecycle management

### AIRegistry

Central registry for managing AI provider plugins. Provides:

- Plugin registration and discovery
- Instance management
- Configuration validation

## Adding a New Provider

1. Create a new directory under `providers/` for your provider
2. Create a plugin class that inherits from `AIPlugin`
3. Implement the `AIInterface` methods
4. Register your plugin using the `@register_plugin` decorator

Example:

```python
from ai.base import AIPlugin, AIInterface
from ai.registry import register_plugin

class MyProvider(AIPlugin):
    name = "myprovider"
    
    def get_interface(self) -> AIInterface:
        return MyProviderInterface(self.config)

@register_plugin
class MyProviderInterface(AIInterface):
    # Implement interface methods
    pass
```

## Usage

```python
from ai import get_plugin, list_plugins

# List available providers
print("Available providers:", list_plugins())

# Get a provider instance
provider = await get_plugin("sambanova", config={"api_key": "..."})

# Use the provider
result = await provider.analyze_email({"subject": "Hello", "body": "..."})
```

## Testing

Run the test suite with:

```bash
pytest tests/ai/
```

## License

[Your License Here]
