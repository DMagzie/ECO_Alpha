"""
ECO Tools Explorer GUI - Configuration

Feature flags and configuration settings for optional functionality.
Allows enabling/disabling features without code changes.
"""

# Feature flags for optional functionality
FEATURES = {
    'geometry_builder': {
        'enabled': True,  # Master enable/disable
        'show_in_nav': True,  # Show in navigation menu
        'beta': True,  # Show beta badge
        'show_warning': True,  # Show experimental warning
        'require_confirmation': False  # Ask before first use
    },
    'template_browser': {
        'enabled': True,
        'show_in_nav': True,
        'beta': False
    },
    'advanced_editing': {
        'enabled': True,
        'show_in_nav': False,  # Accessed via other pages
        'beta': False
    }
}


def is_feature_enabled(feature_name: str) -> bool:
    """
    Check if an optional feature is enabled

    Args:
        feature_name: Name of the feature to check

    Returns:
        True if feature is enabled and available
    """
    feature = FEATURES.get(feature_name, {})
    return feature.get('enabled', False)


def get_feature_config(feature_name: str) -> dict:
    """
    Get full configuration for a feature

    Args:
        feature_name: Name of the feature

    Returns:
        Dictionary with feature configuration
    """
    return FEATURES.get(feature_name, {})


def should_show_in_nav(feature_name: str) -> bool:
    """
    Check if feature should appear in navigation

    Args:
        feature_name: Name of the feature

    Returns:
        True if feature should be in nav menu
    """
    if not is_feature_enabled(feature_name):
        return False

    feature = FEATURES.get(feature_name, {})
    return feature.get('show_in_nav', False)


def get_enabled_features() -> list:
    """
    Get list of all enabled features

    Returns:
        List of enabled feature names
    """
    return [name for name, config in FEATURES.items() if config.get('enabled', False)]


# UI Configuration
UI_CONFIG = {
    'page_title': 'ECO Tools Explorer',
    'page_icon': '🏗️',
    'layout': 'wide',
    'sidebar_state': 'expanded'
}


# Export configuration
EXPORT_CONFIG = {
    'default_format': 'emjson',
    'available_formats': ['emjson', 'cibd22x', 'hbjson'],
    'auto_validate': True
}


# Import configuration
IMPORT_CONFIG = {
    'auto_detect_format': True,
    'supported_formats': ['emjson', 'cibd22x', 'gem', 'hbjson'],
    'max_file_size_mb': 50
}
