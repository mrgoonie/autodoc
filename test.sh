#!/bin/bash
# Test script for AutoDoc AI
echo "Running AutoDoc AI test with GitHub repository"
python3.11 -m autodocai.cli info https://github.com/mrgoonie/searchapi
echo "Running quick generate test with minimal processing"
