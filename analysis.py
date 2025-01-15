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
operator_select = pn.widgets.CheckBoxGroup(
    name='Operators',
    options=list(data['Operator'].unique()),
    value=[],
    inline=False,
    width=200
)

game_type_select = pn.widgets.CheckBoxGroup(
    name='Game Types',
    options=list(data['Game Type'].unique()),
    value=[],
    inline=False,
    width=200
)

map_select = pn.widgets.CheckBoxGroup(
    name='Maps',
    options=list(data['Map'].unique()),
    value=[],
    inline=False,
    width=200
)

date_range = pn.widgets.DatetimeRangePicker(
    name='Date Range',
    start=data['Local Time'].min().replace(tzinfo=None),
    end=data['Local Time'].max().replace(tzinfo=None),
    value=(data['Local Time'].min().replace(tzinfo=None),
           data['Local Time'].max().replace(tzinfo=None)),
    width=200
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
    print(f"Operator filter: {operator}")
    print(f"Game Type filter: {game_type}")
    print(f"Map filter: {map_name}")
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
        width=600
    )
    skill_plot.update_traces(line_color='#00ff00', line_width=2)
    skill_plot.update_layout(template="plotly_dark")
    
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
    
    # Combine plots in a grid layout
    layout = pn.Column(
        pn.Row(skill_plot_pane, kd_by_hour_pane),
        pn.Row(accuracy_hist_pane, kd_hist_pane),
        pn.Row(skill_hist_pane, metrics_plot_pane),
        pn.Row(headshot_plot_pane, damage_plot_pane),
        pn.Row(outcome_plot_pane, map_performance_pane),
        pn.Row(activity_heatmap_pane),
        sizing_mode='stretch_width',
        height=1800
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
    
    return pn.Card(
        pn.Column(
            pn.pane.Markdown("### Performance Metrics", margin=(0,0,15,0), align='center'),
            pn.pane.Markdown(f"**Skill Rating:** {avg_skill}", align='center'),
            pn.pane.Markdown(f"**K/D Ratio:** {kd_ratio}", align='center'),
            pn.pane.Markdown(f"**Win Rate:** {win_rate}%", align='center'),
            pn.pane.Markdown(f"**Accuracy:** {accuracy}%", align='center'),
            pn.pane.Markdown("---", margin=(10,0), align='center'),
            pn.pane.Markdown("### Kill Streaks", margin=(15,0,15,0), align='center'),
            pn.pane.Markdown(f"**Best Streak:** {kill_streak}", align='center'),
            pn.pane.Markdown("---", margin=(10,0), align='center'),
            pn.pane.Markdown("### Time Stats", margin=(15,0,15,0), align='center'),
            pn.pane.Markdown(f"**Kills/min:** {kills_per_min}", align='center'),
            pn.pane.Markdown(f"**Total Time:** {total_time}m", align='center'),
        ),
        title='Performance Summary',
        css_classes=['stats-card'],
        width=220,
        styles={
            'background': 'rgb(30, 30, 30)',
            'color': 'white',
            'border': '1px solid #444',
            'border-radius': '8px',
            'box-shadow': '0 2px 4px rgba(0,0,0,0.2)'
        }
    )

# Define CSS styles
css = """
.dashboard-title {
    color: #FF5733;
    font-size: 32px;
    margin-bottom: 20px;
}
"""

# Layout the dashboard
dashboard = pn.Column(
    pn.pane.HTML("<h1 class='dashboard-title'>Gaming Performance Dashboard</h1>", stylesheets=[css]),
    pn.Row(
        pn.Column(
            operator_select,
            game_type_select,
            map_select,
            date_range,
            create_stats,
            width=250
        ),
        create_plots,
        align='center'
    ),
    styles={'margin': '0 auto'}
)

# Serve the dashboard
dashboard.show()
