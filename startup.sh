#!/bin/bash

# Set default port if not provided
if [ -z "$PORT" ]; then
  export PORT=8501
fi

# Start Streamlit application
streamlit run app/dashboard.py --server.port=$PORT --server.address=0.0.0.0 