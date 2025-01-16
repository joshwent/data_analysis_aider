import pandas as pd
import panel as pn
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from config import *

pn.extension('plotly', css_files=['styles.css'])

# Load and process data once
data = pd.read_csv('data.csv')
data['Local Time'] = pd.to_datetime(data['UTC Timestamp'])
data['Accuracy'] = (data['Hits'] / data['Shots']).clip(0, 1)
data['KD_Ratio'] = data['Kills'] / data['Deaths'].replace(0, 1)
data['Match_Won'] = data['Match Outcome'].str.lower() == 'win'

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
    min_height=400,
    active=[0],  # Open first panel by default
    sizing_mode='stretch_height'
)


# Calculate default date range
default_start = data['Local Time'].min().replace(tzinfo=None)
default_end = data['Local Time'].max().replace(tzinfo=None)

date_range = pn.widgets.DatetimeRangePicker(
    name='Date Range',
    start=default_start,
    end=default_end,
    value=(default_start, default_end),
    width=250,
    styles={
        'background': 'rgb(30, 30, 30)',
        'padding': '12px',
        'border-radius': '8px',
        'margin-top': '20px',
        'width': '100%'
    }
)

# Create plots using hvPlot
def get_filtered_data(operators, game_types, maps, date_range):
    """
    Filter data based on selected criteria. Results are cached to prevent redundant filtering.
    """
    try:
        # Convert lists to tuples for hashing
        operators = tuple(operators) if operators else ()
        game_types = tuple(game_types) if game_types else ()
        maps = tuple(maps) if maps else ()
        date_range = tuple(date_range) if date_range else ()
        
        filtered = data.loc[:]  # Use .loc for efficient view
        
        # Apply filters efficiently
        if any([operators, game_types, maps]):
            mask = pd.Series(True, index=filtered.index)
            if operators:
                mask &= filtered['Operator'].isin(operators)
            if game_types:
                mask &= filtered['Game Type'].isin(game_types)
            if maps:
                mask &= filtered['Map'].isin(maps)
            filtered = filtered[mask]
        
        # Date range filter
        if date_range:
            start_time = pd.Timestamp(date_range[0]).tz_localize(local_tz)
            end_time = pd.Timestamp(date_range[1]).tz_localize(local_tz)
            filtered = filtered[
                (filtered['Local Time'] >= start_time) &
                (filtered['Local Time'] <= end_time)
            ]

        logger.info(
            f"Filtered data: {len(filtered)}/{len(data)} rows "
            f"(operators={operators}, game_types={game_types}, "
            f"maps={maps}, date_range={date_range})"
        )
        
        return filtered
    except Exception as e:
        logger.error(f"Error filtering data: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error

# Store plot references
_plot_refs = {}

def clear_plot_refs():
    """Clear stored plot references and clean up memory"""
    try:
        global _plot_refs
        if _plot_refs:
            for ref in _plot_refs.values():
                if hasattr(ref, 'object') and hasattr(ref.object, 'data'):
                    ref.object.data = []  # Clear plot data
            _plot_refs.clear()
        
        if pn.state.curdoc is not None:
            for root in pn.state.curdoc.roots:
                if hasattr(root, 'children'):
                    root.children = []  # Clear children
            pn.state.curdoc.clear()
    except Exception as e:
        logger.error(f"Error clearing plot references: {e}")

@pn.depends(operator_select.param.value, game_type_select.param.value, 
            map_select.param.value, date_range.param.value, watch=False)
def create_plots(operator, game_type, map_name, date_range):
    # Convert lists to tuples for hashing
    operator = tuple(operator) if isinstance(operator, list) else operator
    game_type = tuple(game_type) if isinstance(game_type, list) else game_type
    map_name = tuple(map_name) if isinstance(map_name, list) else map_name
    date_range = tuple(date_range) if isinstance(date_range, list) else date_range
    
    filtered_data = get_filtered_data(operator, game_type, map_name, date_range)
    
    # Always clear references before creating new plots
    clear_plot_refs()
    
    if filtered_data.empty:
        return pn.Column(
            pn.pane.Markdown("No data matches the selected filters."),
            styles={'color': 'var(--text-secondary)', 'text-align': 'center', 'padding': '2rem'}
        )
    
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
        height=350,
        color_discrete_sequence=['#5B9AFF']
    )
    skill_plot.update_layout(
        autosize=True,
        margin=dict(l=50, r=50, t=50, b=50)
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
    
    # Convert Plotly figures to Panel panes with stored references
    _plot_refs['skill'] = pn.pane.Plotly(skill_plot)
    _plot_refs['kd_hour'] = pn.pane.Plotly(kd_by_hour)
    _plot_refs['accuracy'] = pn.pane.Plotly(accuracy_hist)
    _plot_refs['kd_hist'] = pn.pane.Plotly(kd_hist)
    _plot_refs['skill_hist'] = pn.pane.Plotly(skill_hist)
    _plot_refs['metrics'] = pn.pane.Plotly(metrics_plot)
    _plot_refs['map_perf'] = pn.pane.Plotly(map_performance)
    _plot_refs['headshot'] = pn.pane.Plotly(headshot_plot)
    _plot_refs['damage'] = pn.pane.Plotly(damage_plot)
    _plot_refs['outcome'] = pn.pane.Plotly(outcome_plot)
    
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
    
    _plot_refs['heatmap'] = pn.pane.Plotly(activity_heatmap)
    
    # Create a responsive grid layout for plots with fixed column widths
    layout = pn.GridBox(
        _plot_refs['skill'],
        _plot_refs['kd_hour'],
        _plot_refs['accuracy'],
        _plot_refs['kd_hist'],
        _plot_refs['skill_hist'],
        _plot_refs['metrics'],
        _plot_refs['headshot'],
        _plot_refs['damage'],
        _plot_refs['outcome'],
        _plot_refs['map_perf'],
        _plot_refs['heatmap'],
        ncols=2,
        sizing_mode='stretch_width',
        styles={
            'grid-gap': '1rem',
            'padding': '1rem',
            'background': 'var(--bg-dark)',
            'margin': '0 auto'  # Center the grid
        }
    )
    return layout

# Create stats cards
@pn.depends(operator_select.param.value, game_type_select.param.value,
            map_select.param.value, date_range.param.value, watch=False)
def create_stats(operator, game_type, map_name, date_range):
    # Convert lists to tuples for hashing
    operator = tuple(operator) if isinstance(operator, list) else operator
    game_type = tuple(game_type) if isinstance(game_type, list) else game_type
    map_name = tuple(map_name) if isinstance(map_name, list) else map_name
    date_range = tuple(date_range) if isinstance(date_range, list) else date_range
    
    filtered_data = get_filtered_data(operator, game_type, map_name, date_range)
    
    # Use pre-calculated metrics for better performance
    if filtered_data.empty:
        return pn.Row(
            pn.pane.Markdown("No data matches the selected filters.", styles={
                'color': 'var(--text-secondary)',
                'text-align': 'center',
                'padding': '2rem',
                'width': '100%'
            })
        )

    # Calculate all stats at once using vectorized operations
    stats_dict = {
        'avg_skill': filtered_data['Skill'].mean(),
        'kd_ratio': filtered_data['KD_Ratio'].mean(),
        'win_rate': 100 * filtered_data['Match_Won'].mean(),
        'accuracy': 100 * filtered_data['Accuracy'].mean(),
        'kill_streak': filtered_data['Longest Streak'].max(),
        'kills_per_min': (filtered_data['Kills'].sum() / filtered_data['Lifetime Time Played'].sum() * 60),
        'total_time': filtered_data['Lifetime Time Played'].sum()
    }
    
    # Round all values
    stats_dict = {k: round(float(v or 0), 2) for k, v in stats_dict.items()}
    
    # Create performance summary row with the calculated stats
    stats = [
        ("SKILL", stats_dict['avg_skill'], "var(--primary-color)"),
        ("K/D", stats_dict['kd_ratio'], "var(--accent-color)"),
        ("WIN", f"{stats_dict['win_rate']}%", "var(--success-color)"),
        ("ACC", f"{stats_dict['accuracy']}%", "var(--warning-color)"),
        ("STREAK", stats_dict['kill_streak'], "var(--danger-color)"),
        ("K/MIN", stats_dict['kills_per_min'], "var(--primary-color)"),
        ("TIME", f"{stats_dict['total_time']}m", "var(--accent-color)")
    ]
    
    stat_elements = []
    for label, value, color in stats:
        stat_elements.append(
            pn.pane.Markdown(
                f"<div class='stat-label'>{label}</div><div class='stat-value' style='color: {color}'>{value}</div>",
                styles={
                    'display': 'inline-block',
                    'padding': '0 24px',
                    'text-align': 'center',
                    'border-right': '1px solid var(--border-color)',
                }
            )
        )
    
    summary_row = pn.Row(
        *stat_elements,
        styles={
            'background': 'var(--bg-card)',
            'border': '1px solid var(--border-color)',
            'border-radius': '12px',
            'padding': '16px',
            'margin': '8px 0',
            'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
            'align-items': 'center',
            'justify-content': 'center'
        },
        sizing_mode='stretch_width'
    )
    
    return summary_row

# Initialize Panel with minimal CSS
pn.extension('plotly')
pn.config.raw_css.append(open('styles.css').read())

# Layout the dashboard
# Initialize dashboard with configuration
dashboard = pn.template.FastListTemplate(
    title=DASHBOARD_TITLE,
    sidebar_width=SIDEBAR_WIDTH,
    theme=THEME
)

# Pre-calculate all common metrics once at load time
data['Hour'] = data['Local Time'].dt.hour
data['Day'] = data['Local Time'].dt.day_name()
data['Accuracy'] = (data['Hits'] / data['Shots'].replace(0, 1)).clip(0, 1)
data['KD_Ratio'] = data['Kills'] / data['Deaths'].replace(0, 1)
data['Headshot_Ratio'] = (data['Headshots'] / data['Kills']).fillna(0)
data['Match_Won'] = data['Match Outcome'].str.lower() == 'win'
data['Lifetime_Minutes'] = data['Lifetime Time Played']

# Add components to the sidebar
# Create a sidebar container with proper sizing
sidebar_content = pn.Column(
    pn.pane.Markdown("## Filters", styles={'color': 'var(--text-primary)', 'margin-bottom': '1rem'}),
    date_range,
    filter_accordion,
    styles={'background': 'var(--bg-card)', 'border-radius': '8px', 'padding': '1rem'},
    margin=(0, 10),
    width=300,
    sizing_mode='stretch_height'
)

# Add components to template
dashboard.sidebar.append(sidebar_content)
dashboard.main.append(pn.Column(
    create_stats,
    pn.layout.Divider(margin=(20, 0)),
    create_plots,
    sizing_mode='stretch_width'
))

if __name__ == '__main__':
    dashboard.show()
