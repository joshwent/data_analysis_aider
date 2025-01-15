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

# Create plots using hvPlot
def get_filtered_data(operator, game_type):
    filtered = data.copy()
    if operator != 'All':
        filtered = filtered[filtered['Operator'] == operator]
    if game_type != 'All':
        filtered = filtered[filtered['Game Type'] == game_type]
    return filtered

@pn.depends(operator_select, game_type_select)
def create_plots(operator, game_type):
    filtered_data = get_filtered_data(operator, game_type)
    
    # Calculate metrics
    filtered_data['Accuracy'] = (filtered_data['Hits'] / filtered_data['Shots']).round(3)
    filtered_data['KD_Ratio'] = (filtered_data['Kills'] / filtered_data['Deaths']).round(2)
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
    
    # KD ratio heatmap by hour
    kd_by_hour = filtered_data.groupby('Hour')['KD_Ratio'].mean().hvplot.heatmap(
        title="Average K/D Ratio by Hour",
        height=300,
        cmap='RdYlGn',
        colorbar=True
    )
    
    # Accuracy distribution
    accuracy_hist = filtered_data.hvplot.hist(
        'Accuracy',
        bins=20,
        title="Accuracy Distribution",
        height=300,
        color='orange'
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
    return pn.GridSpec(
        height=1000,
        ncols=2,
        sizing_mode='stretch_width'
    )[
        (0, 0): skill_plot,
        (0, 1): kd_by_hour,
        (1, 0): accuracy_hist,
        (1, 1): metrics_plot,
        (2, slice(0, 2)): top_maps
    ]

# Create stats cards
@pn.depends(operator_select, game_type_select)
def create_stats(operator, game_type):
    filtered_data = get_filtered_data(operator, game_type)
    
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
    total_time = filtered_data['Time Played'].sum()
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
        pn.Column(operator_select, game_type_select, create_stats),
        create_plots
    )
)

# Serve the dashboard
dashboard.show()
