"""
QGIS FLUX AI Toolbox.
"""

def classFactory(iface):
    """Load the plugin class. This is the entry point for QGIS plugins."""
    from .plugin import FluxPlugin
    return FluxPlugin(iface)
