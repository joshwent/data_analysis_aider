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
    
    skill_plot = filtered_data.hvplot.line(
        x='UTC Timestamp', 
        y='Skill', 
        title="Skill Progression Over Time",
        line_width=3,
        height=300,
        grid=True
    )
    
    kd_plot = filtered_data.hvplot.scatter(
        x='Kills', 
        y='Deaths',
        title="Kills vs Deaths",
        height=300,
        grid=True,
        color='red'
    )
    
    accuracy_plot = filtered_data.hvplot.bar(
        'Game Type',
        (filtered_data['Hits'] / (filtered_data['Hits'] + filtered_data['Misses'])).round(3),
        title="Accuracy by Game Type",
        height=300,
        color='green'
    )
    
    return pn.Column(skill_plot, pn.Row(kd_plot, accuracy_plot))

# Create stats cards
@pn.depends(operator_select, game_type_select)
def create_stats(operator, game_type):
    filtered_data = get_filtered_data(operator, game_type)
    
    avg_skill = filtered_data['Skill'].mean().round(2)
    total_kills = filtered_data['Kills'].sum()
    win_rate = (filtered_data['Match Outcome'] == 'win').mean().round(3) * 100
    
    return pn.Card(
        pn.Column(
            pn.pane.Markdown(f"### Average Skill: {avg_skill}"),
            pn.pane.Markdown(f"### Total Kills: {total_kills}"),
            pn.pane.Markdown(f"### Win Rate: {win_rate}%"),
        ),
        title='Statistics',
        css_classes=['stats-card'],
        width=300,
        styles={'background': 'rgb(30, 30, 30)'}
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
    pn.pane.HTML("<h1 class='dashboard-title'>Gaming Performance Dashboard</h1>", styles=dict(background="none")),
    pn.Row(
        pn.Column(operator_select, game_type_select, create_stats),
        create_plots
    ),
    css=css
)

# Serve the dashboard
dashboard.show()
