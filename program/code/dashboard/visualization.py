
import streamlit as st
import plotly.graph_objects as go
from constants import machine_state

@st.cache_data(show_spinner=False)
def visualise_time_series(df, variable_title, idle_bands, run_bands, alerts_indices, file_name):
    # Determine threshold and bands based on machine_state
    bands = idle_bands if machine_state == 'idle' else run_bands

    # Create Plotly figure
    fig = go.Figure()

    opacity = 0.2
    line_width = 0.5

    # Add background color bands
    fig.add_hrect(y0=bands['low'][1], y1=bands['low'][2], line_width=line_width, fillcolor="green", opacity=opacity, name='Normal')
    fig.add_hrect(
                y0=bands['low'][1],
                y1=bands['low'][0],
                line_width=line_width,
                fillcolor="yellow",
                opacity=opacity,
                name="LOW"
            )
    fig.add_hrect(
                y0=bands['low'][2],
                y1=bands['low'][3],
                line_width=line_width,
                fillcolor="yellow",
                opacity=opacity,
                name="LOW"
            )
    fig.add_hrect(
                y0=bands['medium'][1],
                y1=bands['medium'][0],
                line_width=line_width,
                fillcolor="orange",
                opacity=opacity,
                name="MEDIUM"
            )
    fig.add_hrect(
                y0=bands['medium'][2],
                y1=bands['medium'][3],
                line_width=line_width,
                fillcolor="orange",
                opacity=opacity,
                name="MEDIUM"
            )
    fig.add_hrect(
                y0=bands['high'][1],
                y1=bands['high'][1] - 30,
                line_width=line_width,
                fillcolor="red",
                opacity=opacity,
                name="HIGH"
            )
    fig.add_hrect(
                y0=bands['high'][2],
                y1=bands['high'][2] + 30,
                line_width=line_width,
                fillcolor="red",
                opacity=opacity,
                name="HIGH"
            )


    size = 8

    # Add sensor value line plot
    fig.add_trace(go.Scatter(x=df['Time'], y=df[variable_title], mode='lines', name='Sensor Value', line=dict(color='blue')))

    # Filter and add alert scatter plot (separate traces for each severity)
    for severity in ['low', 'medium', 'high', "3-sigma"]:  # Iterate through all severities
        severity_alerts = alerts_indices[alerts_indices['severity'] == severity]
        fig.add_trace(go.Scatter(
            x=df.loc[severity_alerts['alert_index'], 'Time'],
            y=df.loc[severity_alerts['alert_index'], variable_title],
            mode='markers',
            marker=dict(
                color='yellow' if severity == 'low' else 'orange' if severity == 'medium' else 'red' if severity == 'high' else 'purple',
                size=8,
                line=dict(width=2, color='black') if severity == '3-sigma' else None
            ),
            name=f'Alert ({severity})',
            showlegend=True  # Always show in legend
        ))

    highest_severity_band = bands['high']
    lower_bound, upper_bound = highest_severity_band[1] - 2, highest_severity_band[2] + 2

    # Set layout and display
    fig.update_layout(
        title=f'Sensor Value Over Time for {file_name}',
        xaxis_title='Time',
        yaxis_title=variable_title,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        yaxis_range=[lower_bound, upper_bound]  # Set default zoom
    )

    st.plotly_chart(fig)