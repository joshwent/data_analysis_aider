import pandas as pd
import panel as pn
import hvplot.pandas
import holoviews as hv

# Enable Panel extension with a modern theme
pn.extension(sizing_mode="stretch_width")
pn.config.theme = 'dark'

# Load the CSV data
csv_file = 'data.csv'  # Replace with your CSV file path
data = pd.read_csv(csv_file)

# Inspect the data
print(data.head())

data['UTC Timestamp'] = pd.to_datetime(data['UTC Timestamp'])

print(data.columns)

# Create filter widgets
operator_select = pn.widgets.Select(
    name='Operator', 
    options=['All'] + list(data['Operator'].unique()),
    value='All'
)

game_type_select = pn.widgets.Select(
    name='Game Type',
    options=['All'] + list(data['Game Type'].unique()),
    value='All'
)

map_select = pn.widgets.Select(
    name='Map',
    options=['All'] + list(data['Map'].unique()),
    value='All'
)

date_range = pn.widgets.DateRangeSlider(
    name='Date Range',
    start=data['UTC Timestamp'].min(),
    end=data['UTC Timestamp'].max(),
    value=(data['UTC Timestamp'].min(), data['UTC Timestamp'].max())
)

kd_range = pn.widgets.RangeSlider(
    name='K/D Ratio Range',
    start=0,
    end=5,
    value=(0, 5),
    step=0.1
)

# Create plots using hvPlot
def get_filtered_data(operator, game_type, map_name, date_range, kd_range):
    filtered = data.copy()
    
    # Basic filters
    if operator != 'All':
        filtered = filtered[filtered['Operator'] == operator]
    if game_type != 'All':
        filtered = filtered[filtered['Game Type'] == game_type]
    if map_name != 'All':
        filtered = filtered[filtered['Map'] == map_name]
    
    # Date range filter
    filtered = filtered[
        (filtered['UTC Timestamp'] >= pd.Timestamp(date_range[0])) &
        (filtered['UTC Timestamp'] <= pd.Timestamp(date_range[1]))
    ]
    
    # Calculate and filter by KD ratio
    filtered['KD_Ratio'] = filtered['Kills'] / filtered['Deaths']
    filtered = filtered[
        (filtered['KD_Ratio'] >= kd_range[0]) &
        (filtered['KD_Ratio'] <= kd_range[1])
    ]
    
    return filtered

@pn.depends(operator_select, game_type_select, map_select, date_range, kd_range)
def create_plots(operator, game_type, map_name, date_range, kd_range):
    filtered_data = get_filtered_data(operator, game_type, map_name, date_range, kd_range)
    
    # Calculate metrics with proper handling of edge cases
    filtered_data['Accuracy'] = (filtered_data['Hits'] / filtered_data['Shots']).round(3)
    filtered_data['Accuracy'] = filtered_data['Accuracy'].clip(0, 1)  # Limit to valid range
    filtered_data['KD_Ratio'] = filtered_data.apply(
        lambda row: row['Kills'] / row['Deaths'] if row['Deaths'] > 0 else row['Kills'],
        axis=1
    ).round(2)
    filtered_data['Hour'] = filtered_data['UTC Timestamp'].dt.hour
    
    # Skill progression over time
    skill_plot = filtered_data.hvplot.line(
        x='UTC Timestamp', 
        y='Skill',
        title="Skill Progression Over Time",
        line_width=2,
        height=300,
        grid=True,
        color='#00ff00'
    )
    
    # KD ratio by hour as a bar chart
    kd_by_hour = filtered_data.groupby('Hour')['KD_Ratio'].mean().hvplot.bar(
        title="Average K/D Ratio by Hour",
        height=300,
        color='#00ff00',
        xlabel='Hour of Day',
        ylabel='Average K/D Ratio'
    )
    
    # Accuracy distribution (filtered)
    valid_accuracy = filtered_data[
        (filtered_data['Accuracy'] >= 0) & 
        (filtered_data['Accuracy'] <= 1) & 
        (filtered_data['Shots'] > 0)
    ]
    accuracy_hist = valid_accuracy.hvplot.hist(
        'Accuracy',
        bins=30,
        title="Accuracy Distribution",
        height=300,
        color='orange',
        xlabel='Accuracy %',
        ylabel='Number of Matches'
    )
    
    # Performance metrics over time
    metrics_plot = filtered_data.hvplot.line(
        x='UTC Timestamp',
        y=['KD_Ratio', 'Accuracy'],
        title="Performance Metrics Over Time",
        height=300,
        grid=True,
        line_width=2
    )
    
    # Top 5 maps performance
    map_stats = filtered_data.groupby('Map')[['Kills', 'Deaths', 'Accuracy']].mean()
    map_stats['Score'] = map_stats['Kills'] - map_stats['Deaths'] + map_stats['Accuracy']*10
    top_maps = map_stats.nlargest(5, 'Score').hvplot.bar(
        'Score',
        title="Top 5 Maps Performance",
        height=300,
        color='purple'
    )
    
    # Combine plots in a grid layout
    layout = pn.Column(
        pn.Row(skill_plot, kd_by_hour),
        pn.Row(accuracy_hist, metrics_plot),
        top_maps,
        sizing_mode='stretch_width',
        height=1000
    )
    return layout

# Create stats cards
@pn.depends(operator_select, game_type_select, map_select, date_range, kd_range)
def create_stats(operator, game_type, map_name, date_range, kd_range):
    filtered_data = get_filtered_data(operator, game_type, map_name, date_range, kd_range)
    
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
            pn.pane.Markdown("## Performance Metrics"),
            pn.pane.Markdown(f"**Average Skill Rating:** {avg_skill}"),
            pn.pane.Markdown(f"**K/D Ratio:** {kd_ratio} ({total_kills}/{total_deaths})"),
            pn.pane.Markdown(f"**Win Rate:** {win_rate}%"),
            pn.pane.Markdown(f"**Accuracy:** {accuracy}%"),
            pn.pane.Markdown(f"**Average Score:** {avg_score}"),
            pn.pane.Markdown("## Streaks"),
            pn.pane.Markdown(f"**Best Kill Streak:** {kill_streak}"),
            pn.pane.Markdown("## Efficiency"),
            pn.pane.Markdown(f"**Kills per Minute:** {kills_per_min}"),
            pn.pane.Markdown(f"**Total Time Played:** {total_time} minutes"),
        ),
        title='Statistics',
        css_classes=['stats-card'],
        width=400,
        styles={
            'background': 'rgb(30, 30, 30)',
            'color': 'white',
            'border': '1px solid #444'
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
            kd_range,
            create_stats
        ),
        create_plots
    )
)

# Serve the dashboard
dashboard.show()
