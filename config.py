import datetime

# Dashboard settings
DASHBOARD_TITLE = "Gaming Performance Analytics"
SIDEBAR_WIDTH = 300
THEME = "dark"

# Cache settings
CACHE_TTL = 300  # 5 minutes
CACHE_SIZE = 256  # Increased cache size

# Data settings
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOCAL_TIMEZONE = datetime.datetime.now().astimezone().tzinfo

# Plot settings
PLOT_HEIGHT = 300
PLOT_WIDTH = 600
PLOT_TEMPLATE = "plotly_dark"

# Color schemes
COLORS = {
    'skill': '#5B9AFF',
    'kd': '#00D1B2',
    'win': '#6CCF8E',
    'accuracy': '#FF9900',
    'streak': '#FF5286'
}
