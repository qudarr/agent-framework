# Copyright (c) Microsoft. All rights reserved.

"""Accounting Close Workflow - Month-end close orchestration.

This workflow demonstrates:
- Coordinating multiple specialized agents
- Sequential execution with data passing
- Month-end close automation with AR and cashflow analysis

Use case: Automated month-end close process.
Invoice Insights Agent analyzes AR, Cashflow Anomaly Agent detects irregularities,
and a Summarizer creates the final close report.
"""

import json
import os
from pathlib import Path
from typing import Any

from agent_framework import AgentExecutorResponse, WorkflowBuilder
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential


def get_close_checklist() -> str:
    """Retrieve the month-end close checklist."""
    data_path = Path(__file__).parent / "data" / "monthly_close_checklist.json"
    
    try:
        with open(data_path, "r") as f:
            checklist = json.load(f)
    except FileNotFoundError:
        return "Error: Close checklist file not found."
    
    result = f"Month-End Close Checklist for {checklist['month']}:\n\n"
    
    for task in checklist["tasks"]:
        result += f"{task['id']}. {task['task']}\n"
        result += f"   Owner: {task['owner']}\n"
        result += f"   Priority: {task['priority']}\n"
        result += f"   Status: {task['status']}\n"
        result += f"   Description: {task['description']}\n\n"
    
    result += "Notes:\n"
    for note in checklist["notes"]:
        result += f"- {note}\n"
    
    return result


# Create Azure AI Agent client
try:
    chat_client = AzureAIAgentClient(
        project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
        model_deployment_name=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME"),
        async_credential=AzureCliCredential(),
    )
except Exception:
    # Gracefully handle missing credentials
    chat_client = None

# Create Invoice Insights agent - analyzes AR invoices
invoice_agent = chat_client.create_agent(
    name="InvoiceReviewer",
    instructions=(
        "You are the Invoice Insights specialist for the month-end close process. "
        "Analyze AR invoices and provide a comprehensive summary including:\n"
        "1. Total invoices and amounts by status (paid, pending, overdue)\n"
        "2. Any overdue invoices requiring immediate attention\n"
        "3. Revenue projections and collection rates\n"
        "4. Recommendations for collection activities\n\n"
        "Request the user to provide invoice summary data, then analyze it thoroughly."
    ),
) if chat_client else None

# Create Cashflow Anomaly agent - detects unusual patterns
cashflow_agent = chat_client.create_agent(
    name="CashflowAnalyzer",
    instructions=(
        "You are the Cashflow Anomaly Detection specialist for the month-end close process. "
        "Analyze cashflow transactions and provide a report including:\n"
        "1. Monthly cashflow summary (income vs expenses)\n"
        "2. Any detected anomalies or unusual patterns\n"
        "3. Category-specific trends or concerns\n"
        "4. Recommendations for investigation\n\n"
        "Request the user to provide cashflow data, then analyze it for irregularities."
    ),
) if chat_client else None

# Create Summarizer agent - creates final close report
summarizer_agent = chat_client.create_agent(
    name="CloseSummarizer",
    instructions=(
        "You are the Month-End Close Summarizer. "
        "You receive analysis from the Invoice Insights and Cashflow Anomaly agents. "
        "Create a comprehensive month-end close report that includes:\n\n"
        "1. Executive Summary\n"
        "   - Overall close status\n"
        "   - Key metrics (revenue, expenses, net cashflow)\n\n"
        "2. Invoice Analysis Highlights\n"
        "   - Summary from Invoice Insights Agent\n"
        "   - Collection issues and recommendations\n\n"
        "3. Cashflow Analysis Highlights\n"
        "   - Summary from Cashflow Anomaly Agent\n"
        "   - Anomalies requiring attention\n\n"
        "4. Action Items\n"
        "   - Critical tasks to complete the close\n"
        "   - Issues requiring management review\n\n"
        "Format the report professionally and highlight critical items."
    ),
) if chat_client else None

# Build workflow: Invoice Agent → Cashflow Agent → Summarizer
workflow = None
if chat_client:
    workflow = (
        WorkflowBuilder(
            name="Accounting Close Workflow",
            description="Month-end close orchestration workflow (Invoice Insights → Cashflow Anomaly → Close Summary)",
        )
        .set_start_executor(invoice_agent)
        .add_edge(invoice_agent, cashflow_agent)
        .add_edge(cashflow_agent, summarizer_agent)
        .build()
    )


def main():
    """Launch the accounting close workflow in DevUI."""
    import logging

    from agent_framework.devui import serve

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    logger.info("Starting Accounting Close Workflow")
    logger.info("Available at: http://localhost:8092")
    logger.info("\nThis workflow demonstrates:")
    logger.info("- Sequential agent coordination")
    logger.info("- Path: Invoice Insights → Cashflow Anomaly → Close Summary")
    logger.info("- Month-end close automation")
    logger.info("\nNote: Make sure 'az login' has been run for authentication")

    if workflow:
        serve(entities=[workflow], port=8092, auto_open=True)
    else:
        logger.error("Error: Could not create workflow. Check Azure credentials.")


if __name__ == "__main__":
    main()
