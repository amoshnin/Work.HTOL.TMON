
import os
import pickle
import pandas as pd
import streamlit as st
from datetime import datetime
from anomaly_detection import detect_sensor_anomalies, group_alerts, anomaly_detection_3_sigma_rule
from constants import CACHE_DIR
from utils import extract_date, hash_hyperparameters


os.makedirs(CACHE_DIR, exist_ok=True)

@st.cache_data(show_spinner=False)
def process_file(file_path, outlier_tolerance, grouping_time_window, anomaly_threshold, selected_variable, bands):
    # Read the first row to get the event date
    with open(file_path, 'r') as f:
        first_row = f.readline()
    event_date = extract_date(first_row)

    # Read the CSV, skipping the first 3 rows (including the header with the event date)
    df = pd.read_csv(file_path, skiprows=3)

    if not all(col in df.columns for col in [selected_variable]):
        print(f"Skipping file {file_path} due to missing columns.")
        return None, None, None
    else:
        df = df[['Time', selected_variable]]

    # Convert the 'Time' column to datetime, assuming it contains only time information
    df['Time'] = pd.to_datetime(df['Time'], format='%H:%M:%S').dt.time

    # Combine the event date with the time information
    if event_date:
        df['Time'] = df['Time'].apply(lambda x: datetime.combine(event_date, x))
    else:
        print("Warning: Could not extract event date from the first row.")

    alerts_indices = detect_sensor_anomalies(
        df,
        selected_variable,
        bands["idle_bands"],
        bands["run_bands"],
        outlier_tolerance=outlier_tolerance,
    )
    three_sigma_alerts = anomaly_detection_3_sigma_rule(df, bands["idle_bands"], bands["run_bands"], anomaly_threshold, selected_variable)

    grouped_alerts_indices = group_alerts(df, alerts_indices, grouping_time_window, selected_variable)
    grouped_3_sigma_alerts_indices = group_alerts(df, three_sigma_alerts, grouping_time_window, selected_variable)

    all_alerts_indices = pd.concat([grouped_alerts_indices, grouped_3_sigma_alerts_indices])

    return df, all_alerts_indices, event_date


@st.cache_data(show_spinner=False)  # Add caching to this function
def process_HTOL_data(HTOL_name, outlier_tolerance, grouping_time_window, anomaly_threshold, start_datetime, end_datetime, selected_variable, bands):
    alert_counts = {'low': 0, 'medium': 0, 'high': 0, '3-sigma': 0}
    alert_data = {}

    hyperparameter_hash = hash_hyperparameters(outlier_tolerance, grouping_time_window, anomaly_threshold, selected_variable, bands)
    cache_subdir = os.path.join(CACHE_DIR, HTOL_name, hyperparameter_hash)
    os.makedirs(cache_subdir, exist_ok=True)

    file_progress = st.progress(0, text="Processing files...")
    total_files = sum(1 for file_name in os.listdir(HTOL_name) if "HTOL" in file_name)
    processed_files = 0

    for file_name in os.listdir(HTOL_name):
        if "HTOL" in file_name:
            file_path = os.path.join(HTOL_name, file_name)
            file_mtime = os.path.getmtime(file_path)
            cache_file = os.path.join(cache_subdir, f"{file_name}_{hyperparameter_hash}.pkl")

            if os.path.exists(cache_file) and os.path.getmtime(cache_file) > file_mtime:
                with open(cache_file, 'rb') as f:
                    df, grouped_alerts_indices, event_date = pickle.load(f)
            else:
                df, grouped_alerts_indices, event_date = process_file(file_path, outlier_tolerance, grouping_time_window, anomaly_threshold, selected_variable, bands)

                if df is None or grouped_alerts_indices is None or event_date is None:
                    total_files = total_files - 1
                    continue

                with open(cache_file, 'wb') as f:
                    pickle.dump((df, grouped_alerts_indices, event_date), f)

            if start_datetime and end_datetime:
                df = df[(df['Time'] >= start_datetime) & (df['Time'] <= end_datetime)]

                grouped_alerts_indices = grouped_alerts_indices[
                    grouped_alerts_indices['alert_index'].isin(df.index)
                ]

            # Count alerts by severity
            for severity in grouped_alerts_indices['severity'].unique():
                alert_counts[severity] += (grouped_alerts_indices['severity'] == severity).sum()

            # Store alert data for later visualization
            alert_data[file_name] = {
                'df': df,
                'grouped_alerts_indices': grouped_alerts_indices,
                'event_date': event_date
            }

            processed_files += 1
            progress_percentage = int((processed_files / total_files) * 100)
            file_progress.progress(processed_files / total_files, text=f"Processing {file_name}... ({progress_percentage}%)")

    return alert_counts, alert_data
    # alert_counts = {'low': 0, 'medium': 0, 'high': 0, '3-sigma': 0}
    # alert_data = {}

    # file_progress = st.progress(0, text="Processing files...")
    # total_files = sum(1 for file_name in os.listdir(HTOL_name) if "HTOL" in file_name)
    # processed_files = 0

    # for file_name in os.listdir(HTOL_name):
    #     if "HTOL" in file_name:
    #         file_path = os.path.join(HTOL_name, file_name)
    #         df, grouped_alerts_indices, event_date = process_file(file_path, outlier_tolerance, grouping_time_window, anomaly_threshold)

    #         # Count alerts by severity
    #         for severity in grouped_alerts_indices['severity'].unique():
    #             alert_counts[severity] += (grouped_alerts_indices['severity'] == severity).sum()

    #         # Store alert data for later visualization
    #         alert_data[file_name] = {
    #             'df': df,
    #             'grouped_alerts_indices': grouped_alerts_indices ,
    #             'event_date': event_date
    #         }

    #         processed_files += 1
    #         progress_percentage = int((processed_files / total_files) * 100)
    #         file_progress.progress(processed_files / total_files, text=f"Processing {file_name}... ({progress_percentage}%)")
    # return alert_counts, alert_data