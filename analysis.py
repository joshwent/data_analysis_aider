import pandas as pd
import panel as pn
import hvplot.pandas

# Enable Panel extension
pn.extension()

# Load the CSV data
csv_file = 'data.csv'  # Replace with your CSV file path
data = pd.read_csv(csv_file)

# Inspect the data
print(data.head())

# Create plots using hvPlot
line_plot = data.hvplot.line(x='UTC Timestamp', y='Skill', title="Skill Over Time", line_width=2)



# Layout the dashboard
dashboard = pn.Column(
    pn.pane.Markdown("# Interactive Data Dashboard"),
    pn.Row(line_plot),
)

# Serve the dashboard
dashboard.show()