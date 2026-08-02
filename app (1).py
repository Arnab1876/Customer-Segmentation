import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import plotly.colors

st.set_page_config(layout="wide")
st.title("RFM Customer Segmentation Dashboard")

# --- Data Loading and RFM Calculation (Re-creating steps from notebook) ---

# @st.cache_data is important for performance in Streamlit apps
@st.cache_data
def load_data():
    data = pd.read_csv("/content/rfm_data.csv")
    data['PurchaseDate'] = pd.to_datetime(data['PurchaseDate'])
    return data

data = load_data()

# Calculate Recency, Frequency, Monetary
current_date = datetime.now() # For consistency with the original notebook
data['Recency'] = (current_date - data['PurchaseDate']).dt.days

frequency_data = data.groupby('CustomerID')['OrderID'].count().reset_index()
frequency_data.rename(columns={'OrderID': 'Frequency'}, inplace=True)
data = data.merge(frequency_data, on='CustomerID', how='left')

monetary_data = data.groupby('CustomerID')['TransactionAmount'].sum().reset_index()
monetary_data.rename(columns={'TransactionAmount': 'MonetaryValue'}, inplace=True)
data = data.merge(monetary_data, on='CustomerID', how='left')

# Assign RFM Scores
recency_scores = [5, 4, 3, 2, 1]
frequency_scores = [1, 2, 3, 4, 5]
monetary_scores = [1, 2, 3, 4, 5]

data['RecencyScore'] = pd.cut(data['Recency'], bins=5, labels=recency_scores, duplicates='drop')
data['FrequencyScore'] = pd.cut(data['Frequency'], bins=5, labels=frequency_scores, duplicates='drop')
data['MonetaryScore'] = pd.cut(data['MonetaryValue'], bins=5, labels=monetary_scores, duplicates='drop')

data['RecencyScore'] = data['RecencyScore'].astype(int)
data['FrequencyScore'] = data['FrequencyScore'].astype(int)
data['MonetaryScore'] = data['MonetaryScore'].astype(int)

# Calculate RFM Score and Value Segment
data['RFM_Score'] = data['RecencyScore'] + data['FrequencyScore'] + data['MonetaryScore']
segment_labels = ['Low-Value', 'Mid-Value', 'High-Value']
# Ensure q is not too large for the number of unique scores
num_unique_scores = data['RFM_Score'].nunique()
q_val = min(3, num_unique_scores) # Use 3 if enough unique values, otherwise fewer
if q_val > 0:
    data['Value Segment'] = pd.qcut(data['RFM_Score'], q=q_val, labels=segment_labels[:q_val], duplicates='drop')
else:
    data['Value Segment'] = 'Undefined'

# Assign RFM Customer Segments
data['RFM Customer Segments'] = ''
data.loc[data['RFM_Score'] >= 9, 'RFM Customer Segments'] = 'Champions'
data.loc[(data['RFM_Score'] >= 6) & (data['RFM_Score'] < 9), 'RFM Customer Segments'] = 'Potential Loyalists'
data.loc[(data['RFM_Score'] >= 5) & (data['RFM_Score'] < 6), 'RFM Customer Segments'] = 'At Risk Customers'
data.loc[(data['RFM_Score'] >= 4) & (data['RFM_Score'] < 5), 'RFM Customer Segments'] = "Can't Lose"
data.loc[(data['RFM_Score'] >= 3) & (data['RFM_Score'] < 4), 'RFM Customer Segments'] = "Lost"

# --- Streamlit App Layout ---
st.header("1. RFM Value Segment Distribution")
segment_counts = data['Value Segment'].value_counts().reset_index()
segment_counts.columns = ['Value Segment', 'Count']
pastel_colors = px.colors.qualitative.Pastel
fig_segment_dist = px.bar(segment_counts, x='Value Segment', y='Count',
                          color='Value Segment', color_discrete_sequence=pastel_colors,
                          title='RFM Value Segment Distribution')
fig_segment_dist.update_layout(xaxis_title='RFM Value Segment', yaxis_title='Count', showlegend=False)
st.plotly_chart(fig_segment_dist, use_container_width=True)

st.header("2. RFM Customer Segments by Value")
segment_product_counts = data.groupby(['Value Segment', 'RFM Customer Segments']).size().reset_index(name='Count')
segment_product_counts = segment_product_counts.sort_values('Count', ascending=False)
fig_treemap_segment_product = px.treemap(segment_product_counts,
                                         path=['Value Segment', 'RFM Customer Segments'],
                                         values='Count',
                                         color='Value Segment', color_discrete_sequence=px.colors.qualitative.Pastel,
                                         title='RFM Customer Segments by Value')
st.plotly_chart(fig_treemap_segment_product, use_container_width=True)

st.header("3. Distribution of RFM Values within Champions Segment")
champions_segment = data[data['RFM Customer Segments'] == 'Champions']
if not champions_segment.empty:
    fig_champions_rfm = go.Figure()
    fig_champions_rfm.add_trace(go.Box(y=champions_segment['RecencyScore'], name='Recency'))
    fig_champions_rfm.add_trace(go.Box(y=champions_segment['FrequencyScore'], name='Frequency'))
    fig_champions_rfm.add_trace(go.Box(y=champions_segment['MonetaryScore'], name='Monetary'))
    fig_champions_rfm.update_layout(title='Distribution of RFM Values within Champions Segment',
                                    yaxis_title='RFM Value', showlegend=True)
    st.plotly_chart(fig_champions_rfm, use_container_width=True)
else:
    st.write("No Champions segment data to display RFM value distribution.")

st.header("4. Correlation Matrix of RFM Values within Champions Segment")
if not champions_segment.empty:
    correlation_matrix = champions_segment[['RecencyScore', 'FrequencyScore', 'MonetaryScore']].corr()
    fig_heatmap = go.Figure(data=go.Heatmap(
                       z=correlation_matrix.values,
                       x=correlation_matrix.columns,
                       y=correlation_matrix.columns,
                       colorscale='RdBu',
                       colorbar=dict(title='Correlation')))
    fig_heatmap.update_layout(title='Correlation Matrix of RFM Values within Champions Segment')
    st.plotly_chart(fig_heatmap, use_container_width=True)
else:
    st.write("No Champions segment data to display correlation matrix.")

st.header("5. Comparison of RFM Segments (Customer Count)")
segment_counts_overall = data['RFM Customer Segments'].value_counts()
fig_segment_compare = go.Figure(data=[go.Bar(x=segment_counts_overall.index, y=segment_counts_overall.values,
                                            marker=dict(color=pastel_colors))])
champions_color = 'rgb(158, 202, 225)'
fig_segment_compare.update_traces(marker_color=[champions_color if segment == 'Champions' else pastel_colors[i]
                                                for i, segment in enumerate(segment_counts_overall.index)],
                                  marker_line_color='rgb(8, 48, 107)',
                                  marker_line_width=1.5, opacity=0.6)
fig_segment_compare.update_layout(title='Comparison of RFM Segments',
                                  xaxis_title='RFM Segments',
                                  yaxis_title='Number of Customers', showlegend=False)
st.plotly_chart(fig_segment_compare, use_container_width=True)

st.header("6. Comparison of RFM Segments based on Recency, Frequency, and Monetary Scores")
segment_scores = data.groupby('RFM Customer Segments')[['RecencyScore', 'FrequencyScore', 'MonetaryScore']].mean().reset_index()
fig_scores_compare = go.Figure()
fig_scores_compare.add_trace(go.Bar(x=segment_scores['RFM Customer Segments'], y=segment_scores['RecencyScore'], name='Recency Score', marker_color='rgb(158,202,225)'))
fig_scores_compare.add_trace(go.Bar(x=segment_scores['RFM Customer Segments'], y=segment_scores['FrequencyScore'], name='Frequency Score', marker_color='rgb(94,158,217)'))
fig_scores_compare.add_trace(go.Bar(x=segment_scores['RFM Customer Segments'], y=segment_scores['MonetaryScore'], name='Monetary Score', marker_color='rgb(32,102,148)'))
fig_scores_compare.update_layout(title='Comparison of RFM Segments based on Recency, Frequency, and Monetary Scores',
                                 xaxis_title='RFM Segments', yaxis_title='Score', barmode='group', showlegend=True)
st.plotly_chart(fig_scores_compare, use_container_width=True)
