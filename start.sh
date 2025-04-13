#!/bin/bash
pip install -r requirements.txt
python -m gunicorn app:app