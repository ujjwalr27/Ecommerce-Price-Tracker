#!/bin/bash
if [ -z "$PORT" ]; then
  export PORT=8501
fi

streamlit run app/dashboard.py --server.port=$PORT --server.address=0.0.0.0 