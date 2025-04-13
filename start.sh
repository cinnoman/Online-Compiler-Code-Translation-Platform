#!/bin/bash
pip install -r requirements.txt
gunicorn app:app --bind 0.0.0.0:$PORT --log-level debug