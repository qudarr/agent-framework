# Copyright (c) Microsoft. All rights reserved.
"""Invoice Insights Agent for AR invoice analysis.

This agent uses Azure AI Agent with Azure CLI authentication.
Make sure to run 'az login' before starting devui.
"""

import json
import os
from pathlib import Path
from typing import Annotated

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from pydantic import Field


def get_invoice_summary(
    status_filter: Annotated[
        str, Field(description="Filter invoices by status: 'all', 'paid', 'pending', or 'overdue'")
    ] = "all",
) -> str:
    """Get a summary of AR invoices filtered by status."""
    data_path = Path(__file__).parent / "data" / "sample_invoices.json"
    
    try:
        with open(data_path, "r") as f:
            invoices = json.load(f)
    except FileNotFoundError:
        return "Error: Invoice data file not found."
    
    # Filter invoices
    if status_filter.lower() != "all":
        filtered = [inv for inv in invoices if inv["status"].lower() == status_filter.lower()]
    else:
        filtered = invoices
    
    if not filtered:
        return f"No invoices found with status '{status_filter}'."
    
    total_amount = sum(inv["amount"] for inv in filtered)
    count = len(filtered)
    
    summary = f"Invoice Summary (Status: {status_filter}):\n"
    summary += f"Total Invoices: {count}\n"
    summary += f"Total Amount: ${total_amount:,.2f}\n\n"
    summary += "Details:\n"
    
    for inv in filtered:
        summary += f"- {inv['invoice_id']}: {inv['company_name']} - ${inv['amount']:,.2f} ({inv['status']})\n"
    
    return summary


def get_overdue_invoices() -> str:
    """Get detailed information about overdue invoices."""
    data_path = Path(__file__).parent / "data" / "sample_invoices.json"
    
    try:
        with open(data_path, "r") as f:
            invoices = json.load(f)
    except FileNotFoundError:
        return "Error: Invoice data file not found."
    
    overdue = [inv for inv in invoices if inv["status"].lower() == "overdue"]
    
    if not overdue:
        return "Great news! No overdue invoices found."
    
    total_overdue = sum(inv["amount"] for inv in overdue)
    
    result = f"Overdue Invoices Alert:\n"
    result += f"Total Overdue: {len(overdue)} invoice(s)\n"
    result += f"Total Amount: ${total_overdue:,.2f}\n\n"
    result += "Details:\n"
    
    for inv in overdue:
        result += f"- {inv['invoice_id']}: {inv['company_name']}\n"
        result += f"  Amount: ${inv['amount']:,.2f}\n"
        result += f"  Due Date: {inv['due_date']}\n"
        items_desc = inv['items'][0]['description'] if inv.get('items') and len(inv['items']) > 0 else "No items"
        result += f"  Items: {items_desc}\n\n"
    
    return result


def analyze_invoice_by_company(
    company_name: Annotated[str, Field(description="The company name to search for")],
) -> str:
    """Retrieve and analyze invoices for a specific company."""
    data_path = Path(__file__).parent / "data" / "sample_invoices.json"
    
    try:
        with open(data_path, "r") as f:
            invoices = json.load(f)
    except FileNotFoundError:
        return "Error: Invoice data file not found."
    
    # Case-insensitive search
    company_invoices = [
        inv for inv in invoices 
        if company_name.lower() in inv["company_name"].lower()
    ]
    
    if not company_invoices:
        return f"No invoices found for company matching '{company_name}'."
    
    total = sum(inv["amount"] for inv in company_invoices)
    
    result = f"Invoice Analysis for '{company_name}':\n"
    result += f"Total Invoices: {len(company_invoices)}\n"
    result += f"Total Amount: ${total:,.2f}\n\n"
    
    for inv in company_invoices:
        result += f"Invoice {inv['invoice_id']}:\n"
        result += f"  Amount: ${inv['amount']:,.2f}\n"
        result += f"  Status: {inv['status']}\n"
        result += f"  Due Date: {inv['due_date']}\n"
        items_desc = inv['items'][0]['description'] if inv.get('items') and len(inv['items']) > 0 else "No items"
        result += f"  Items: {items_desc}\n\n"
    
    return result


def get_revenue_projection() -> str:
    """Calculate revenue projections based on pending and paid invoices."""
    data_path = Path(__file__).parent / "data" / "sample_invoices.json"
    
    try:
        with open(data_path, "r") as f:
            invoices = json.load(f)
    except FileNotFoundError:
        return "Error: Invoice data file not found."
    
    paid = sum(inv["amount"] for inv in invoices if inv["status"] == "paid")
    pending = sum(inv["amount"] for inv in invoices if inv["status"] == "pending")
    overdue = sum(inv["amount"] for inv in invoices if inv["status"] == "overdue")
    
    result = "Revenue Projection Report:\n\n"
    result += f"Realized Revenue (Paid): ${paid:,.2f}\n"
    result += f"Expected Revenue (Pending): ${pending:,.2f}\n"
    result += f"At Risk Revenue (Overdue): ${overdue:,.2f}\n\n"
    result += f"Total Potential Revenue: ${paid + pending + overdue:,.2f}\n"
    result += f"Collection Rate: {(paid / (paid + pending + overdue) * 100):.1f}%\n"
    
    return result


# Agent instance following Agent Framework conventions
agent = ChatAgent(
    name="InvoiceInsightsAgent",
    chat_client=AzureAIAgentClient(
        project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
        model_deployment_name=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME"),
        async_credential=AzureCliCredential(),
    ),
    instructions="""
    You are an AR (Accounts Receivable) invoice analysis assistant. You help finance teams
    understand their invoice status, identify overdue payments, analyze customer payment
    patterns, and project revenue.
    
    You have access to tools that can:
    - Summarize invoices by status (all, paid, pending, overdue)
    - Identify and analyze overdue invoices
    - Retrieve invoices for specific companies
    - Calculate revenue projections and collection rates
    
    Always provide clear, actionable insights and highlight important information like
    overdue amounts or payment trends.
    """,
    tools=[
        get_invoice_summary,
        get_overdue_invoices,
        analyze_invoice_by_company,
        get_revenue_projection,
    ],
)


def main():
    """Launch the Invoice Insights agent in DevUI."""
    import logging

    from agent_framework.devui import serve

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    logger.info("Starting Invoice Insights Agent")
    logger.info("Available at: http://localhost:8090")
    logger.info("Entity ID: agent_InvoiceInsightsAgent")
    logger.info("Note: Make sure 'az login' has been run for authentication")

    # Launch server with the agent
    serve(entities=[agent], port=8090, auto_open=True)


if __name__ == "__main__":
    main()
