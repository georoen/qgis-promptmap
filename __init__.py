"""
PromptMap — AI cartography for QGIS.
"""

def classFactory(iface):
    """Load the plugin class. This is the entry point for QGIS plugins."""
    from .plugin import PromptMapPlugin
    return PromptMapPlugin(iface)
