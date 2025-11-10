#!/bin/bash
cd /home/kavia/workspace/code-generation/financial-document-evaluation-platform-221929-221938/financial_evaluation_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

