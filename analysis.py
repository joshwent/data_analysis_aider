import pandas as pd
import panel as pn
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Enable Panel extension with a modern theme
pn.extension(sizing_mode="stretch_width")
pn.config.theme = 'dark'

# Load the CSV data
csv_file = 'data.csv'  # Replace with your CSV file path
data = pd.read_csv(csv_file)

# Inspect the data
print(data.head())

import datetime

# Convert UTC timestamps to local time and ensure proper timezone handling
data['UTC Timestamp'] = pd.to_datetime(data['UTC Timestamp']).dt.tz_localize('UTC')
local_tz = datetime.datetime.now().astimezone().tzinfo
data['Local Time'] = data['UTC Timestamp'].dt.tz_convert(local_tz)

print(data.columns)

# Create filter widgets with checkboxes
def create_checkbox_group(name, options, width=220):
    select_all = pn.widgets.Checkbox(name='Select All', value=False, width=width)
    checkbox_group = pn.widgets.CheckBoxGroup(
        name=name,
        options=sorted(options),
        value=[],
        inline=False,
        width=width,
        styles={
            'background': 'var(--bg-card)',
            'padding': '12px',
            'border-radius': '8px',
            'margin-bottom': '8px'
        }
    )
    
    def update_checkboxes(event):
        if event.new:
            checkbox_group.value = checkbox_group.options
        else:
            checkbox_group.value = []
    
    select_all.param.watch(update_checkboxes, 'value')
    
    return pn.Column(select_all, checkbox_group)

operator_group = create_checkbox_group('Select Operators', list(data['Operator'].unique()))
operator_select = operator_group[1]

game_type_group = create_checkbox_group('Select Game Types', list(data['Game Type'].unique()))
game_type_select = game_type_group[1]

map_group = create_checkbox_group('Select Maps', list(data['Map'].unique()))
map_select = map_group[1]

# Create filter accordion
filter_accordion = pn.Accordion(
    ('Operators', operator_group),
    ('Game Types', game_type_group),
    ('Maps', map_group),
    width=250,
    active=[0],  # Open first panel by default
    sizing_mode='fixed'
)


date_range = pn.widgets.DatetimeRangePicker(
    name='Date Range',
    start=data['Local Time'].min().replace(tzinfo=None),
    end=data['Local Time'].max().replace(tzinfo=None),
    value=(data['Local Time'].min().replace(tzinfo=None),
           data['Local Time'].max().replace(tzinfo=None)),
    width=220,
    styles={
        'background': 'rgb(30, 30, 30)',
        'padding': '10px',
        'border-radius': '4px',
        'margin-top': '20px'
    }
)

# Create plots using hvPlot
def get_filtered_data(operators, game_types, maps, date_range):
    filtered = data.copy()
    
    # Basic filters with checkbox lists
    if operators:
        filtered = filtered[filtered['Operator'].isin(operators)]
    if game_types:
        filtered = filtered[filtered['Game Type'].isin(game_types)]
    if maps:
        filtered = filtered[filtered['Map'].isin(maps)]
    
    # Date range filter with proper timezone handling
    start_time = pd.Timestamp(date_range[0]).tz_localize(local_tz)
    end_time = pd.Timestamp(date_range[1]).tz_localize(local_tz)
    
    # Ensure timestamps are in the correct timezone before comparison
    filtered = filtered[
        (filtered['Local Time'] >= start_time) &
        (filtered['Local Time'] <= end_time)
    ]

    # Add debug print statements
    print(f"Filtering stats:")
    print(f"Total rows before filter: {len(data)}")
    print(f"Operators filter: {operators}")
    print(f"Game Types filter: {game_types}")
    print(f"Maps filter: {maps}")
    print(f"Date range: {start_time} to {end_time}")
    print(f"Remaining rows after filter: {len(filtered)}")
    
    return filtered

@pn.depends(operator_select, game_type_select, map_select, date_range)
def create_plots(operator, game_type, map_name, date_range):
    filtered_data = get_filtered_data(operator, game_type, map_name, date_range)
    
    # Calculate metrics with proper handling of edge cases
    filtered_data['Accuracy'] = (filtered_data['Hits'] / filtered_data['Shots']).round(3)
    filtered_data['Accuracy'] = filtered_data['Accuracy'].clip(0, 1)  # Limit to valid range
    filtered_data['KD_Ratio'] = filtered_data.apply(
        lambda row: row['Kills'] / row['Deaths'] if row['Deaths'] > 0 else row['Kills'],
        axis=1
    ).round(2)
    # Extract time-based features
    # Extract time-based features using local time
    filtered_data['Hour'] = filtered_data['Local Time'].dt.hour
    filtered_data['Day'] = filtered_data['Local Time'].dt.day_name()
    
    # Skill progression over time
    skill_plot = px.line(
        filtered_data,
        x='Local Time',
        y='Skill',
        title="Skill Progression Over Time",
        height=300,
        width=600,
        color_discrete_sequence=['#5B9AFF']
    )
    skill_plot.update_traces(line_width=2)
    skill_plot.update_layout(
        template="plotly_dark",
        xaxis_title='Time',
        yaxis_title='Skill Rating'
    )
    
    # KD ratio by hour as a bar chart with 12-hour format
    hourly_data = filtered_data.groupby('Hour')['KD_Ratio'].mean().reset_index()
    hourly_data['Hour_12'] = hourly_data['Hour'].apply(
        lambda x: f"{x if 0 < x < 12 else 12 if x == 12 else x-12} {'AM' if x < 12 else 'PM'}"
    )
    kd_by_hour = px.bar(
        hourly_data,
        x='Hour_12',
        y='KD_Ratio',
        title="Average K/D Ratio by Hour",
        height=300,
        width=600,
        color_discrete_sequence=['#00ff00']
    )
    kd_by_hour.update_layout(
        xaxis_title='Hour of Day',
        yaxis_title='Average K/D Ratio',
        template="plotly_dark",
        xaxis_tickangle=45
    )
    
    # Accuracy distribution
    valid_accuracy = filtered_data[
        (filtered_data['Accuracy'] >= 0) & 
        (filtered_data['Accuracy'] <= 1) & 
        (filtered_data['Shots'] > 0)
    ]
    accuracy_hist = px.histogram(
        valid_accuracy,
        x='Accuracy',
        nbins=30,
        title="Accuracy Distribution",
        height=300,
        width=600,
        color_discrete_sequence=['orange']
    )
    accuracy_hist.update_layout(
        xaxis_title='Accuracy %',
        yaxis_title='Number of Matches',
        template="plotly_dark"
    )

    # K/D distribution
    kd_hist = px.histogram(
        filtered_data,
        x='KD_Ratio',
        nbins=30,
        title="K/D Ratio Distribution",
        height=300,
        width=600,
        color_discrete_sequence=['red']
    )
    kd_hist.update_layout(
        xaxis_title='K/D Ratio',
        yaxis_title='Number of Matches',
        template="plotly_dark"
    )

    # Skill distribution
    skill_hist = px.histogram(
        filtered_data,
        x='Skill',
        nbins=30,
        title="Skill Distribution",
        height=300,
        width=600,
        color_discrete_sequence=['cyan']
    )
    skill_hist.update_layout(
        xaxis_title='Skill Rating',
        yaxis_title='Number of Matches',
        template="plotly_dark"
    )
    
    # Performance metrics over time
    metrics_plot = px.line(
        filtered_data,
        x='Local Time',
        y=['KD_Ratio', 'Accuracy'],
        title="Performance Metrics Over Time",
        height=300,
        width=600
    )
    metrics_plot.update_traces(line_width=2)
    metrics_plot.update_layout(template="plotly_dark")
    
    # Headshot ratio over time
    filtered_data['Headshot_Ratio'] = (filtered_data['Headshots'] / filtered_data['Kills']).fillna(0)
    headshot_plot = px.line(
        filtered_data,
        x='Local Time',
        y='Headshot_Ratio',
        title="Headshot Ratio Over Time",
        height=300,
        width=600
    )
    headshot_plot.update_traces(line_color='#ff4d4d', line_width=2)
    headshot_plot.update_layout(
        yaxis_title='Headshot Ratio',
        template="plotly_dark"
    )

    # Damage efficiency (damage done vs taken)
    damage_plot = px.scatter(
        filtered_data,
        x='Damage Taken',
        y='Damage Done',
        title="Damage Efficiency",
        height=300,
        width=600,
        color='Match Outcome',
        trendline="ols"
    )
    damage_plot.update_layout(
        template="plotly_dark",
        showlegend=True
    )

    # Match outcomes pie chart
    outcome_stats = filtered_data['Match Outcome'].value_counts()
    outcome_plot = px.pie(
        values=outcome_stats.values,
        names=outcome_stats.index,
        title="Match Outcomes Distribution",
        height=300,
        width=600,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    outcome_plot.update_layout(template="plotly_dark")

    # Map K/D performance
    map_stats = (filtered_data.groupby('Map')
                .agg({'Kills': 'sum', 'Deaths': 'sum'})
                .reset_index())
    
    # Calculate KD ratio safely
    map_stats['KD'] = (map_stats['Kills'] / map_stats['Deaths'].replace(0, 1)).round(2)
    
    # Sort by KD ratio
    map_stats = map_stats.sort_values('KD', ascending=True)
    
    map_performance = px.bar(
        map_stats,
        x='Map',
        y='KD',
        title="K/D Ratio by Map",
        height=400,
        width=600,
        color_discrete_sequence=['purple']
    )
    map_performance.update_layout(
        xaxis_title='Map',
        yaxis_title='K/D Ratio',
        template="plotly_dark",
        xaxis_tickangle=45
    )
    
    # Convert Plotly figures to Panel panes
    skill_plot_pane = pn.pane.Plotly(skill_plot)
    kd_by_hour_pane = pn.pane.Plotly(kd_by_hour)
    accuracy_hist_pane = pn.pane.Plotly(accuracy_hist)
    kd_hist_pane = pn.pane.Plotly(kd_hist)
    skill_hist_pane = pn.pane.Plotly(skill_hist)
    metrics_plot_pane = pn.pane.Plotly(metrics_plot)
    map_performance_pane = pn.pane.Plotly(map_performance)
    headshot_plot_pane = pn.pane.Plotly(headshot_plot)
    damage_plot_pane = pn.pane.Plotly(damage_plot)
    outcome_plot_pane = pn.pane.Plotly(outcome_plot)
    
    # Create activity heatmap
    activity_df = filtered_data.groupby(['Day', 'Hour']).size().reset_index(name='Count')
    activity_pivot = activity_df.pivot(index='Day', columns='Hour', values='Count').fillna(0)
    
    # Reorder days to start with Monday
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    activity_pivot = activity_pivot.reindex(day_order)
    
    # Convert hour numbers to 12-hour format for heatmap
    hour_labels = [f"{h if 0 < h < 12 else 12 if h == 12 else h-12} {'AM' if h < 12 else 'PM'}" 
                  for h in activity_pivot.columns]
    
    activity_heatmap = go.Figure(data=go.Heatmap(
        z=activity_pivot.values,
        x=hour_labels,
        y=activity_pivot.index,
        colorscale='Viridis',
        hoverongaps=False
    ))
    
    activity_heatmap.update_layout(
        title='Gaming Activity Heatmap',
        xaxis_title='Hour of Day',
        yaxis_title='Day of Week',
        height=400,
        template="plotly_dark",
        xaxis_tickangle=45
    )
    
    activity_heatmap_pane = pn.pane.Plotly(activity_heatmap)
    
    # Create a responsive grid layout for plots with fixed column widths
    layout = pn.GridBox(
        skill_plot_pane,
        kd_by_hour_pane,
        accuracy_hist_pane,
        kd_hist_pane,
        skill_hist_pane,
        metrics_plot_pane,
        headshot_plot_pane,
        damage_plot_pane,
        outcome_plot_pane,
        map_performance_pane,
        activity_heatmap_pane,
        ncols=2,
        sizing_mode='fixed',
        width=1200,
        styles={
            'grid-gap': '1rem',
            'padding': '1rem',
            'background': 'var(--bg-dark)',
            'margin': '0 auto'  # Center the grid
        }
    )
    return layout

# Create stats cards
@pn.depends(operator_select, game_type_select, map_select, date_range)
def create_stats(operator, game_type, map_name, date_range):
    filtered_data = get_filtered_data(operator, game_type, map_name, date_range)
    
    # Calculate basic stats
    avg_skill = filtered_data['Skill'].mean().round(2)
    total_kills = filtered_data['Kills'].sum()
    total_deaths = filtered_data['Deaths'].sum()
    kd_ratio = (total_kills / total_deaths).round(2)
    win_rate = (filtered_data['Match Outcome'] == 'win').mean().round(3) * 100
    accuracy = (filtered_data['Hits'].sum() / filtered_data['Shots'].sum()).round(3) * 100
    avg_score = filtered_data['Score'].mean().round(0)
    
    # Calculate streaks
    kill_streak = filtered_data['Longest Streak'].max()
    
    # Calculate time-based stats
    total_time = filtered_data['Lifetime Time Played'].sum()
    kills_per_min = (total_kills / total_time * 60).round(2)
    
    # Create performance summary row
    summary_row = pn.Row(
        pn.pane.Markdown(
            f"""
            **SKILL** {avg_skill} | 
            **K/D** {kd_ratio} | 
            **WIN** {win_rate}% | 
            **ACC** {accuracy}% | 
            **STREAK** {kill_streak} | 
            **K/MIN** {kills_per_min} | 
            **TIME** {total_time}m
            """,
            styles={
                'background': 'var(--bg-card)',
                'border': '1px solid var(--border-color)',
                'border-radius': '8px',
                'padding': '12px 16px',
                'margin': '4px',
                'font-family': 'Inter, sans-serif',
                'font-size': '14px',
                'color': 'var(--text-primary)',
                'text-align': 'center'
            }
        ),
        sizing_mode='stretch_width'
    )
    
    return summary_row

# Define CSS styles
css = """
:root {
    --primary-color: #5B9AFF;
    --accent-color: #00D1B2;
    --bg-dark: #111217;
    --bg-card: #181B1F;
    --bg-hover: #22252B;
    --text-primary: #D8D9DA;
    --text-secondary: #99A1B2;
    --border-color: #2C3235;
    --panel-header: #22252B;
    --panel-border: #34363C;
    --success-color: #6CCF8E;
    --warning-color: #FF9900;
    --danger-color: #FF5286;
}

body {
    background-color: var(--bg-dark) !important;
    color: var(--text-primary) !important;
    font-family: 'Roboto', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    line-height: 1.5 !important;
}

.dashboard-title {
    color: var(--text-primary);
    font-size: 1.75rem;
    font-weight: 500;
    margin: 1rem 0;
    padding: 0.5rem 1rem;
    border-bottom: 1px solid var(--panel-border);
    background: var(--bg-card);
    letter-spacing: 0.2px;
}

.bk-accordion {
    background: var(--bg-card) !important;
    border-radius: 3px !important;
    border: 1px solid var(--panel-border) !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15) !important;
    overflow: hidden !important;
    margin-bottom: 0.5rem !important;
}

.bk-accordion-header {
    background: var(--panel-header) !important;
    padding: 0.75rem 1rem !important;
    color: var(--text-primary) !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    border: none !important;
    transition: all 0.15s ease !important;
    border-bottom: 1px solid var(--panel-border) !important;
}

.bk-accordion-header:hover {
    background: var(--bg-hover) !important;
    color: var(--primary-color) !important;
}

.bk-accordion-header.active {
    background: var(--bg-hover) !important;
    color: var(--primary-color) !important;
    border-bottom: 2px solid var(--primary-color) !important;
}

.bk-accordion-header button {
    color: inherit !important;
}

.bk-accordion button:before {
    border-color: var(--primary-color) !important;
    opacity: 1 !important;
}

.bk-accordion-content {
    background: var(--bg-card) !important;
    border: none !important;
    padding: 1rem !important;
}

.bk-checkbox-group {
    margin: 0.5rem !important;
    padding: 0.5rem !important;
}

.bk-checkbox-group label {
    color: var(--text-secondary) !important;
    font-size: 0.9rem !important;
    margin: 0.25rem 0 !important;
}

.bk-input {
    background: var(--bg-hover) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    padding: 0.75rem !important;
    transition: all 0.2s ease !important;
}

.bk-input:focus {
    border-color: var(--primary-color) !important;
    box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2) !important;
}

.stats-card {
    background: var(--bg-card) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    transition: transform 0.2s ease !important;
}

.stats-card:hover {
    transform: translateY(-2px) !important;
}

.stats-card .bk-card-header {
    background: var(--bg-hover) !important;
    border-bottom: 1px solid var(--border-color) !important;
    color: var(--primary-color) !important;
    font-weight: 600 !important;
    padding: 1rem !important;
}

.stats-card .markdown {
    padding: 1rem !important;
    text-align: center !important;
    border-radius: 8px !important;
    background: var(--bg-hover) !important;
    margin: 0.25rem !important;
    min-width: 120px !important;
}

.stats-card .markdown h3 {
    color: var(--accent-color) !important;
    font-size: 1.4rem !important;
    margin: 0 0 1rem !important;
    text-align: center !important;
}

.stats-card .markdown strong {
    color: var(--text-primary) !important;
    display: block !important;
    margin-bottom: 0.5rem !important;
}

/* Plot styling */
.plot-container {
    background: var(--bg-card) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    margin: 0.5rem !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
}

.js-plotly-plot .plotly .main-svg {
    background: var(--bg-card) !important;
}

.js-plotly-plot .plotly .modebar {
    background: transparent !important;
}

.js-plotly-plot .plotly .modebar-btn path {
    fill: var(--text-secondary) !important;
}
"""

# Layout the dashboard
dashboard = pn.template.FastListTemplate(
    title="Gaming Performance Analytics",
    sidebar_width=300,
    header_background="#111217",
    header_color="#D8D9DA",
    theme="dark",
    theme_toggle=False,
    main_max_width="1400px"  # Limit maximum width of main content
)

# Add components to the sidebar
dashboard.sidebar.append(
    pn.Column(
        pn.pane.Markdown("## Filters", styles={'color': 'var(--text-primary)', 'margin-bottom': '1rem'}),
        filter_accordion,
        date_range,
        styles={'background': 'var(--bg-card)'},
        margin=(0, 10),
        sizing_mode='stretch_width'
    )
)

# Main content area
dashboard.main.append(
    pn.Column(
        create_stats,
        pn.layout.Divider(margin=(20, 0)),
        create_plots,
        sizing_mode='stretch_width',
        styles={'background': 'var(--bg-dark)'},
        margin=(0, 20)
    )
)

# Serve the dashboard
dashboard.show()
