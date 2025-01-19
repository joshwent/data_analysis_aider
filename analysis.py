import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State, callback, callback_context, no_update
import pandas as pd

# Global variables
global data
data = pd.DataFrame()  # Start with empty DataFrame
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots

# Initialize the Dash app
app = Dash(__name__, 
          external_stylesheets=[dbc.themes.DARKLY],
          meta_tags=[{'name': 'viewport',
                     'content': 'width=device-width, initial-scale=1.0'}])

from html_parser import parse_html_file
import base64
import io


# print(data.columns)

# Create filter widgets with checkboxes
def create_checkbox_group(id_prefix, name, options):
    return html.Div([
        html.Div([
            dbc.Button(
                "Select All",
                id=f"{id_prefix}-select-all",
                color="primary",
                size="sm",
                className="me-2 mb-2"
            ),
            dbc.Button(
                "Deselect All",
                id=f"{id_prefix}-deselect-all", 
                color="secondary",
                size="sm",
                className="mb-2"
            ),
        ]),
        dbc.Checklist(
            id=f"{id_prefix}-checklist",
            options=[{"label": opt, "value": opt} for opt in sorted(options)],
            value=[],
            className="filter-checklist"
        )
    ], className="filter-group")

operator_group = create_checkbox_group('operator', 'Select Operators', [])
game_type_group = create_checkbox_group('game-type', 'Select Game Types', [])
map_group = create_checkbox_group('map', 'Select Maps', [])

# Create filter accordion using Dash components
filter_accordion = dbc.Accordion([
    dbc.AccordionItem(operator_group, title="Operators", item_id="operators"),
    dbc.AccordionItem(game_type_group, title="Game Types", item_id="game-types"),
    dbc.AccordionItem(map_group, title="Maps", item_id="maps")
], active_item="operators", style={"width": "250px"})

# Create date range picker using Dash component
date_range = dcc.DatePickerRange(
    id='date-range-picker',
    min_date_allowed=None,
    max_date_allowed=None,
    initial_visible_month=datetime.datetime.now(),
    start_date=None,
    end_date=None,
    style={
        'background-color': 'rgb(30, 30, 30)',
        'padding': '10px',
        'border-radius': '4px',
        'margin-top': '20px'
    }
)

# Create plots using hvPlot
def get_filtered_data(operators, game_types, maps, date_range):
    # Return empty DataFrame if any filter category is empty
    if not operators or not game_types or not maps:
        return pd.DataFrame(columns=data.columns)
        
    filtered = data.copy()
    
    # Basic filters with checkbox lists
    if operators:
        filtered = filtered[filtered['Operator'].isin(operators)]
    if game_types:
        filtered = filtered[filtered['Game Type'].isin(game_types)]
    if maps:
        filtered = filtered[filtered['Map'].isin(maps)]
    
    # Date range filter with proper timezone handling
    local_tz = datetime.datetime.now().astimezone().tzinfo
    start_time = pd.Timestamp(date_range[0]).tz_localize(local_tz)
    end_time = pd.Timestamp(date_range[1]).tz_localize(local_tz)
    
    # Ensure timestamps are in the correct timezone before comparison
    filtered = filtered[
        (filtered['Local Time'] >= start_time) &
        (filtered['Local Time'] <= end_time)
    ]

    # Add debug print statements
    # print(f"Filtering stats:")
    # print(f"Total rows before filter: {len(data)}")
    # print(f"Operators filter: {operators}")
    # print(f"Game Types filter: {game_types}")
    # print(f"Maps filter: {maps}")
    # print(f"Date range: {start_time} to {end_time}")
    # print(f"Remaining rows after filter: {len(filtered)}")
    
    return filtered

@callback(
    Output('plots-container', 'children'),
    [Input('operator-checklist', 'value'),
     Input('game-type-checklist', 'value'),
     Input('map-checklist', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def create_plots(operator, game_type, map_name, start_date, end_date):
    date_range = (start_date, end_date)
    filtered_data = get_filtered_data(operator, game_type, map_name, date_range)
    
    # Return message if no data after filtering
    if filtered_data.empty:
        return html.Div("Select filters to display charts", 
                       style={'text-align': 'center', 
                             'padding': '20px',
                             'color': 'var(--text-secondary)'})
    
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
    
    # Calculate KD ratio safely, replacing 0 deaths with 1
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
    
    # Create Dash graph components
    plots = [
        dcc.Graph(figure=skill_plot, id='skill-plot'),
        dcc.Graph(figure=kd_by_hour, id='kd-by-hour-plot'),
        dcc.Graph(figure=accuracy_hist, id='accuracy-hist'),
        dcc.Graph(figure=kd_hist, id='kd-hist'),
        dcc.Graph(figure=skill_hist, id='skill-hist'),
        dcc.Graph(figure=metrics_plot, id='metrics-plot'),
        dcc.Graph(figure=map_performance, id='map-performance'),
        dcc.Graph(figure=headshot_plot, id='headshot-plot'),
        dcc.Graph(figure=damage_plot, id='damage-plot'),
        dcc.Graph(figure=outcome_plot, id='outcome-plot')
    ]
    
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
    
    # Add activity heatmap to plots list
    plots.append(dcc.Graph(figure=activity_heatmap, id='activity-heatmap'))
    
    # Create responsive grid layout using Dash
    layout = html.Div(
        plots,
        style={
            'display': 'grid',
            'grid-template-columns': 'repeat(2, 1fr)',
            'gap': '1rem',
            'padding': '1rem',
            'background': 'var(--bg-dark)',
            'margin': '0 auto',
            'max-width': '1200px'
        }
    )
    return layout

# Create stats cards
@callback(
    Output('stats-container', 'children'),
    [Input('operator-checklist', 'value'),
     Input('game-type-checklist', 'value'),
     Input('map-checklist', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def create_stats(operator, game_type, map_name, start_date, end_date):
    date_range = (start_date, end_date)
    filtered_data = get_filtered_data(operator, game_type, map_name, date_range)
    
    # Return empty stats if no data is loaded
    if data.empty:
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H3("No Data Loaded", 
                           className="text-center mb-4",
                           style={'color': 'var(--accent-color)', 'fontSize': '1.4rem'}),
                    html.Div("Please load data using the upload button or example data button above.",
                            className="text-center",
                            style={'color': 'var(--text-secondary)'})
                ])
            ], className="stats-card mb-4")
        ])

    # Calculate stats from filtered data
    total_kills = filtered_data['Kills'].sum() if not filtered_data.empty else 0
    total_deaths = filtered_data['Deaths'].sum() if not filtered_data.empty else 0
    print(f"total kills: {total_kills}, total deaths: {total_deaths}")
    kd_ratio = round(total_kills / (total_deaths or 1), 2)  # Use 1 if total_deaths is 0
    total_wins = filtered_data['Match Outcome'].str.lower().str.contains('win').sum() if not filtered_data.empty else 0
    total_games = len(filtered_data)
    win_rate = round((total_wins / (total_games or 1)) * 100, 1)  # Use 1 if total_games is 0
    total_shots = filtered_data['Shots'].sum() if not filtered_data.empty else 0
    total_hits = filtered_data['Hits'].sum() if not filtered_data.empty else 0
    accuracy = round((total_hits / (total_shots or 1)) * 100, 1)  # Use 1 if total_shots is 0
    avg_score = int(round(filtered_data['Score'].mean(), 0)) if not filtered_data.empty else 0
    
    # Get total time played
    total_seconds = filtered_data['Match Duration'].sum() if not filtered_data.empty else 0
    
    # Format total time
    days = total_seconds // (24 * 60 * 60)
    remaining_seconds = total_seconds % (24 * 60 * 60)
    hours = remaining_seconds // (60 * 60)
    minutes = (remaining_seconds % (60 * 60)) // 60
    total_time = f"{days}d {hours}h {minutes}m"
    
    # Create two cards: one for lifetime stats and one for filtered stats
    lifetime_card = dbc.Card([
        dbc.CardBody([
            html.H3("Lifetime Statistics", 
                    className="text-center mb-4",
                    style={'color': 'var(--accent-color)', 'fontSize': '1.4rem'}),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Strong("Total K/D"),
                        html.Div(f"{kd_ratio}")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Overall Win Rate"),
                        html.Div(f"{win_rate}%")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Lifetime Accuracy"),
                        html.Div(f"{accuracy}%")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Total Play Time"),
                        html.Div(f"{total_time}")
                    ], className="text-center mb-3")
                ]),
            ])
        ])
    ], className="stats-card mb-4")

    # Return message if no data after filtering
    if filtered_data.empty:
        empty_card = html.Div("Select filters to display statistics", 
                       style={'text-align': 'center', 
                             'padding': '20px',
                             'color': 'var(--text-secondary)'})
        return html.Div([lifetime_card, empty_card])

    # Calculate filtered-specific stats
    filtered_avg_skill = round(filtered_data['Skill'].mean(), 2)
    filtered_kills = filtered_data['Kills'].sum()
    filtered_deaths = filtered_data['Deaths'].sum()
    print(f"filtered kills: {filtered_kills}, filtered deaths: {filtered_deaths}")
    filtered_kd = round(filtered_kills / (filtered_deaths or 1), 2)
    filtered_wins = filtered_data['Match Outcome'].str.lower().str.contains('win').sum()
    filtered_total = len(filtered_data)
    filtered_winrate = round((filtered_wins / (filtered_total or 1)) * 100, 1)  # Use 1 if filtered_total is 0
    filtered_accuracy = round((filtered_data['Hits'].sum() / filtered_data['Shots'].sum()) * 100, 1)
    filtered_streak = int(filtered_data['Longest Streak'].max())
    
    filtered_card = dbc.Card([
        dbc.CardBody([
            html.H3("Filtered Performance", 
                    className="text-center mb-4",
                    style={'color': 'var(--accent-color)', 'fontSize': '1.4rem'}),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Strong("Avg Skill Rating"),
                        html.Div(f"{filtered_avg_skill}")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Filtered K/D"),
                        html.Div(f"{filtered_kd}")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Win Rate"),
                        html.Div(f"{filtered_winrate}%")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Accuracy"),
                        html.Div(f"{filtered_accuracy}%")
                    ], className="text-center mb-3")
                ]),
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Strong("Best Streak"),
                        html.Div(f"{filtered_streak}")
                    ], className="text-center")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Matches"),
                        html.Div(f"{filtered_total}")
                    ], className="text-center")
                ]),
            ])
        ])
    ], className="stats-card", style={
        'background': 'rgb(30, 30, 30)',
        'color': 'white',
        'border': '1px solid #444',
        'borderRadius': '8px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.2)'
    })
    
    # Return both cards in a container
    return html.Div([
        lifetime_card,
        filtered_card
    ])

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

# Define the app layout
app.layout = dbc.Container([
    dbc.Row([
        # File upload
        dbc.Col([
            html.H2("Data Import",
                   style={'color': 'var(--text-primary)', 
                         'marginBottom': '1rem'}),
            dbc.Button(
                "Load Example Data",
                id='load-example-data',
                color="secondary",
                className="mb-3",
                style={'width': '100%'}
            ),
            html.Div("- or -", 
                    className="text-center mb-3",
                    style={'color': 'var(--text-secondary)'}),
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select HTML File')
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px 0'
                },
                multiple=False
            )
        ], width=12, style={
            'background': 'var(--bg-card)',
            'padding': '20px',
            'borderRadius': '8px',
            'marginBottom': '20px'
        }),
    ]),
    dbc.Row([
        # Sidebar
        dbc.Col([
            html.H2("Filters", 
                   style={'color': 'var(--text-primary)', 
                         'marginBottom': '1rem'}),
            filter_accordion,
            date_range
        ], width=3, style={
            'background': 'var(--bg-card)',
            'padding': '20px',
            'borderRadius': '8px'
        }),
        
        # Main content
        dbc.Col([
            html.Div(id='stats-container'),
            html.Hr(style={'margin': '20px 0'}),
            html.Div(id='plots-container')
        ], width=9, style={
            'background': 'var(--bg-dark)',
            'padding': '20px'
        })
    ])
], fluid=True, style={'maxWidth': '1400px'})

# Callbacks for select/deselect all buttons
@callback(
    Output('operator-checklist', 'value'),
    [Input('operator-select-all', 'n_clicks'),
     Input('operator-deselect-all', 'n_clicks')],
    [State('operator-checklist', 'options')]
)
def operator_select_all(select_clicks, deselect_clicks, options):
    ctx = callback_context
    if not ctx.triggered:
        return [opt['value'] for opt in options]  # Select all by default
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'operator-select-all':
        return [opt['value'] for opt in options]
    elif button_id == 'operator-deselect-all':
        return []
    return []

@callback(
    Output('game-type-checklist', 'value'),
    [Input('game-type-select-all', 'n_clicks'),
     Input('game-type-deselect-all', 'n_clicks')],
    [State('game-type-checklist', 'options')]
)
def game_type_select_all(select_clicks, deselect_clicks, options):
    ctx = callback_context
    if not ctx.triggered:
        return [opt['value'] for opt in options]  # Select all by default
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'game-type-select-all':
        return [opt['value'] for opt in options]
    elif button_id == 'game-type-deselect-all':
        return []
    return []

@callback(
    Output('map-checklist', 'value'),
    [Input('map-select-all', 'n_clicks'),
     Input('map-deselect-all', 'n_clicks')],
    [State('map-checklist', 'options')]
)
def map_select_all(select_clicks, deselect_clicks, options):
    ctx = callback_context
    if not ctx.triggered:
        return [opt['value'] for opt in options]  # Select all by default
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'map-select-all':
        return [opt['value'] for opt in options]
    elif button_id == 'map-deselect-all':
        return []
    return []

# Callback for loading example data
@callback(
    [Output('upload-data', 'children', allow_duplicate=True),
     Output('operator-checklist', 'options', allow_duplicate=True),
     Output('game-type-checklist', 'options', allow_duplicate=True),
     Output('map-checklist', 'options', allow_duplicate=True),
     Output('date-range-picker', 'min_date_allowed', allow_duplicate=True),
     Output('date-range-picker', 'max_date_allowed', allow_duplicate=True),
     Output('date-range-picker', 'start_date', allow_duplicate=True),
     Output('date-range-picker', 'end_date', allow_duplicate=True)],
    Input('load-example-data', 'n_clicks'),
    prevent_initial_call=True
)
def load_example_data(n_clicks):
    global data
    if n_clicks is None:
        return no_update
        
    try:
        # Load example data from data2.csv
        data = pd.read_csv('data2.csv')
        
        # Apply the same filters as initial CSV data
        data = data[data['Game Type'] != 'Pentathlon Hint (TDM Example: Eliminate the other team or be holding the flag when time runs out.)']
        data = data[data['Game Type'] != 'Training Course']
        data = data[data['Game Type'] != 'Ran-snack']
        data = data[data['Game Type'] != 'Stop and Go']
        data = data[data['Game Type'] != 'Red Light Green Light']
        data = data[data['Game Type'] != 'Prop Hunt']
        
        # Convert timezone
        data['UTC Timestamp'] = pd.to_datetime(data['UTC Timestamp'])
        data['UTC Timestamp'] = data['UTC Timestamp'].dt.tz_localize('UTC')
        local_tz = datetime.datetime.now().astimezone().tzinfo
        data['Local Time'] = data['UTC Timestamp'].dt.tz_convert(local_tz)
        
        # Update filter options
        operator_options = [{"label": opt, "value": opt} for opt in sorted(data['Operator'].unique())]
        game_type_options = [{"label": opt, "value": opt} for opt in sorted(data['Game Type'].unique())]
        map_options = [{"label": opt, "value": opt} for opt in sorted(data['Map'].unique())]
        
        # Update date range
        min_date = data['Local Time'].min().replace(tzinfo=None)
        max_date = data['Local Time'].max().replace(tzinfo=None)
        
        return (
            html.Div([
                html.I(className="fas fa-check-circle", style={'color': 'green', 'marginRight': '10px'}),
                'Example data loaded successfully'
            ]),
            operator_options,
            game_type_options,
            map_options,
            min_date,
            max_date,
            min_date,
            max_date
        )
            
    except Exception as e:
        return (
            html.Div([
                html.I(className="fas fa-exclamation-circle", style={'color': 'red', 'marginRight': '10px'}),
                'Error loading example data: ',
                html.Pre(str(e))
            ]),
            [], [], [], None, None, None, None
        )

# Combined callback for file upload and date picker
@callback(
    [Output('upload-data', 'children'),
     Output('operator-checklist', 'options'),
     Output('game-type-checklist', 'options'),
     Output('map-checklist', 'options'),
     Output('date-range-picker', 'min_date_allowed'),
     Output('date-range-picker', 'max_date_allowed'),
     Output('date-range-picker', 'start_date', allow_duplicate=True),
     Output('date-range-picker', 'end_date', allow_duplicate=True)],
    [Input('upload-data', 'contents'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')],
    [State('upload-data', 'filename')],
    prevent_initial_call=True
)
def update_data(contents, start_date, end_date, filename):
    global data
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # Handle date picker updates
    if triggered_id in ['date-range-picker']:
        if start_date is None:
            start_date = data['Local Time'].min().replace(tzinfo=None)
        if end_date is None:
            end_date = data['Local Time'].max().replace(tzinfo=None)
        return no_update, no_update, no_update, no_update, no_update, no_update, start_date, end_date
    
    # Handle file upload
    if contents is None:
        return html.Div([
            'Drag and Drop or ',
            html.A('Select HTML File')
        ]), [], [], [], None, None, None, None
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        if 'html' in filename.lower():
            # Parse HTML file and update global data
            data = parse_html_file(decoded.decode('utf-8'))
            
            # Apply the same filters as initial CSV data
            data = data[data['Game Type'] != 'Pentathlon Hint (TDM Example: Eliminate the other team or be holding the flag when time runs out.)']
            data = data[data['Game Type'] != 'Training Course']
            data = data[data['Game Type'] != 'Ran-snack']
            data = data[data['Game Type'] != 'Stop and Go']
            data = data[data['Game Type'] != 'Red Light Green Light']
            data = data[data['Game Type'] != 'Prop Hunt']
            
            # Convert timezone
            data['UTC Timestamp'] = pd.to_datetime(data['UTC Timestamp'])
            data['UTC Timestamp'] = data['UTC Timestamp'].dt.tz_localize('UTC')
            local_tz = datetime.datetime.now().astimezone().tzinfo
            data['Local Time'] = data['UTC Timestamp'].dt.tz_convert(local_tz)
            
            # Update filter options
            operator_options = [{"label": opt, "value": opt} for opt in sorted(data['Operator'].unique())]
            game_type_options = [{"label": opt, "value": opt} for opt in sorted(data['Game Type'].unique())]
            map_options = [{"label": opt, "value": opt} for opt in sorted(data['Map'].unique())]
            
            # Update date range
            min_date = data['Local Time'].min().replace(tzinfo=None)
            max_date = data['Local Time'].max().replace(tzinfo=None)
            
            return (
                html.Div([
                    html.I(className="fas fa-check-circle", style={'color': 'green', 'marginRight': '10px'}),
                    f'Successfully loaded {filename}'
                ]),
                operator_options,
                game_type_options,
                map_options,
                min_date,
                max_date,
                min_date,
                max_date
            )
            
    except Exception as e:
        return (
            html.Div([
                html.I(className="fas fa-exclamation-circle", style={'color': 'red', 'marginRight': '10px'}),
                'Error processing file: ',
                html.Pre(str(e))
            ]),
            [], [], [], None, None, None, None
        )

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
