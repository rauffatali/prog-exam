"""
AI Tools Configuration Module

Contains lists of known AI processes and extensions for detection.
"""

# Known AI coding assistants (process names)
AI_PROCESSES = {
    'windows': [
        'github.copilot',
        'copilot',
        'tabnine',
        'kite',
        'intellicode',
        'codex',
        'cursor',
        'windsor',
        'continue',
        'codium',
        'codewhisperer',
        'aws-toolkit',
        'genie',
        'blackbox',
        'askcodi',
        'mutableai',
        'replit-ghostwriter',
        'refact',
        'codegeex',
        'codeium'
    ],
    'linux': [
        'copilot',
        'tabnine',
        'kite',
        'cursor',
        'codium',
        'codewhisperer',
        'genie',
        'blackbox',
        'askcodi',
        'mutableai',
        'refact',
        'codegeex',
        'codeium'
    ],
    'darwin': [  # macOS
        'copilot',
        'tabnine',
        'kite',
        'cursor',
        'codium',
        'codewhisperer',
        'genie',
        'blackbox',
        'askcodi',
        'mutableai',
        'refact',
        'codegeex',
        'codeium'
    ]
}

# Known LLM platforms and AI tools (process names)
LLM_PROCESSES = {
    'windows': [
        'chatgpt',
        'openai',
        'gpt',
        'claude',
        'claude-code',
        'anthropic',
        'gemini',
        'bard',
        'grok',
        'xai-grok',
        'perplexity',
        'pplx',
        'mistral',
        'llama',
        'ollama',
        'huggingface',
        'replit',
        'cohere',
        'ai21',
        'together',
        'runway',
        'midjourney',
        'dalle',
        'stable-diffusion',
        'automatic1111',
        'webui',
        'invokeai'
    ],
    'linux': [
        'chatgpt',
        'openai',
        'gpt',
        'claude',
        'claude-code',
        'anthropic',
        'gemini',
        'bard',
        'grok',
        'xai-grok',
        'perplexity',
        'pplx',
        'mistral',
        'llama',
        'ollama',
        'huggingface',
        'replit',
        'cohere',
        'ai21',
        'together',
        'runway',
        'midjourney',
        'dalle',
        'stable-diffusion',
        'automatic1111',
        'webui',
        'invokeai'
    ],
    'darwin': [  # macOS
        'chatgpt',
        'openai',
        'gpt',
        'claude',
        'claude-code',
        'anthropic',
        'gemini',
        'bard',
        'grok',
        'xai-grok',
        'perplexity',
        'pplx',
        'mistral',
        'llama',
        'ollama',
        'huggingface',
        'replit',
        'cohere',
        'ai21',
        'together',
        'runway',
        'midjourney',
        'dalle',
        'stable-diffusion',
        'automatic1111',
        'webui',
        'invokeai'
    ]
}

# AI extension metadata (for enablement checks)
AI_EXTENSION_META = {
    'github.copilot': {
        'default_enabled': True,  # On by default
        'settings_keys': ['github.copilot.enable'],
        'disable_values': [False]
    },
    'codeium.codeium': {
        'default_enabled': True,
        'settings_keys': ['codeium.enableConfig', 'codeium.enableCodeLens'],
        'disable_values': [False, False]
    },
    'google.geminicodeassist': {
        'default_enabled': True,
        'settings_keys': ['geminicodeassist.enable', 'geminicodeassist.inlineSuggestions.enableAuto'],
        'disable_values': [False, False]
    },
    'blackboxapp.blackbox': {
        'default_enabled': True,
        'settings_keys': ['blackboxapp.blackbox.enable', 'blackboxapp.blackbox.editor.enableAutoCompletions'],
        'disable_values': [False, False]
    },
    'tabnine.tabnine-vscode': {
        'default_enabled': True,
        'settings_keys': ['tabnine.codeLensEnabled', 'tabnine.completionsLoadingIndicatorEnabled'],
        'disable_values': [False, False]
    },
    'danielsanmedium.dscodegpt': {
        'default_enabled': True,
        'settings_keys': ['codegpt.codegpt.enable', 'codegpt.codegpt.editor.enableAutoCompletions'],
        'disable_values': [False, False]
    }, 
    'saoudrizwan.claude-dev': {
        'default_enabled': True,
        'settings_keys': ['saoudrizwan.claude-dev.enable', 'saoudrizwan.claude-dev.editor.enableAutoCompletions'],
        'disable_values': [False, False]
    }
    # Add more as needed
}