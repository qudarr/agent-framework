# Copyright (c) Microsoft. All rights reserved.
"""Cashflow Anomaly Detection Agent for identifying unusual cashflow patterns.

This agent uses Azure AI Agent with Azure CLI authentication.
Make sure to run 'az login' before starting devui.
"""

import csv
import os
from pathlib import Path
from typing import Annotated

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from pydantic import Field


def get_cashflow_summary(
    transaction_type: Annotated[
        str, Field(description="Filter by type: 'all', 'income', or 'expense'")
    ] = "all",
) -> str:
    """Get a summary of cashflow transactions by type."""
    data_path = Path(__file__).parent / "data" / "cashflow_ledger.csv"
    
    try:
        with open(data_path, "r") as f:
            reader = csv.DictReader(f)
            transactions = list(reader)
    except FileNotFoundError:
        return "Error: Cashflow data file not found."
    
    # Filter transactions
    if transaction_type.lower() != "all":
        filtered = [t for t in transactions if t["type"].lower() == transaction_type.lower()]
    else:
        filtered = transactions
    
    if not filtered:
        return f"No transactions found with type '{transaction_type}'."
    
    total_amount = sum(float(t["amount"]) for t in filtered)
    count = len(filtered)
    
    summary = f"Cashflow Summary (Type: {transaction_type}):\n"
    summary += f"Total Transactions: {count}\n"
    summary += f"Net Amount: ${total_amount:,.2f}\n\n"
    summary += "Recent Transactions:\n"
    
    # Show last 5 transactions
    for t in filtered[-5:]:
        summary += f"- {t['date']}: {t['category']} - ${float(t['amount']):,.2f} ({t['description']})\n"
    
    return summary


def detect_anomalies(
    threshold_percent: Annotated[
        float, Field(description="Percentage threshold for detecting anomalies (e.g., 50 for 50%)")
    ] = 50.0,
) -> str:
    """Detect unusual cashflow patterns based on threshold percentage deviation."""
    data_path = Path(__file__).parent / "data" / "cashflow_ledger.csv"
    
    try:
        with open(data_path, "r") as f:
            reader = csv.DictReader(f)
            transactions = list(reader)
    except FileNotFoundError:
        return "Error: Cashflow data file not found."
    
    # Calculate average amounts by category
    category_totals = {}
    category_counts = {}
    
    for t in transactions:
        cat = t["category"]
        amount = abs(float(t["amount"]))
        
        if cat not in category_totals:
            category_totals[cat] = 0
            category_counts[cat] = 0
        
        category_totals[cat] += amount
        category_counts[cat] += 1
    
    category_averages = {
        cat: category_totals[cat] / category_counts[cat] 
        for cat in category_totals
    }
    
    # Find anomalies
    anomalies = []
    for t in transactions:
        cat = t["category"]
        amount = abs(float(t["amount"]))
        avg = category_averages[cat]
        
        if avg > 0:
            deviation = ((amount - avg) / avg) * 100
            if abs(deviation) >= threshold_percent:
                anomalies.append({
                    "date": t["date"],
                    "category": cat,
                    "amount": float(t["amount"]),
                    "average": avg,
                    "deviation": deviation,
                    "description": t["description"]
                })
    
    if not anomalies:
        return f"No anomalies detected with threshold of {threshold_percent}%."
    
    result = f"Anomaly Detection Report (Threshold: {threshold_percent}%):\n\n"
    result += f"Found {len(anomalies)} anomalous transaction(s):\n\n"
    
    for a in anomalies:
        result += f"- {a['date']}: {a['category']}\n"
        result += f"  Amount: ${a['amount']:,.2f}\n"
        result += f"  Category Average: ${a['average']:,.2f}\n"
        result += f"  Deviation: {a['deviation']:.1f}%\n"
        result += f"  Description: {a['description']}\n\n"
    
    return result


def analyze_category_trends(
    category: Annotated[str, Field(description="Category to analyze (e.g., 'Operating Revenue', 'Operating Expenses')")],
) -> str:
    """Analyze trends for a specific cashflow category."""
    data_path = Path(__file__).parent / "data" / "cashflow_ledger.csv"
    
    try:
        with open(data_path, "r") as f:
            reader = csv.DictReader(f)
            transactions = list(reader)
    except FileNotFoundError:
        return "Error: Cashflow data file not found."
    
    # Filter by category (case-insensitive)
    category_txns = [
        t for t in transactions 
        if category.lower() in t["category"].lower()
    ]
    
    if not category_txns:
        return f"No transactions found for category matching '{category}'."
    
    total = sum(float(t["amount"]) for t in category_txns)
    avg = total / len(category_txns)
    
    result = f"Category Trend Analysis: '{category}'\n\n"
    result += f"Total Transactions: {len(category_txns)}\n"
    result += f"Total Amount: ${total:,.2f}\n"
    result += f"Average Amount: ${avg:,.2f}\n\n"
    result += "Transaction History:\n"
    
    for t in category_txns:
        result += f"- {t['date']}: ${float(t['amount']):,.2f} - {t['description']}\n"
    
    return result


def get_monthly_cashflow() -> str:
    """Calculate net cashflow by month."""
    data_path = Path(__file__).parent / "data" / "cashflow_ledger.csv"
    
    try:
        with open(data_path, "r") as f:
            reader = csv.DictReader(f)
            transactions = list(reader)
    except FileNotFoundError:
        return "Error: Cashflow data file not found."
    
    # Group by month
    monthly = {}
    for t in transactions:
        month = t["date"][:7]  # Extract YYYY-MM
        amount = float(t["amount"])
        
        if month not in monthly:
            monthly[month] = {"income": 0, "expense": 0}
        
        if t["type"] == "income":
            monthly[month]["income"] += amount
        else:
            monthly[month]["expense"] += amount
    
    result = "Monthly Cashflow Analysis:\n\n"
    
    for month in sorted(monthly.keys()):
        income = monthly[month]["income"]
        expense = monthly[month]["expense"]
        net = income + expense  # expense is negative
        
        result += f"{month}:\n"
        result += f"  Income: ${income:,.2f}\n"
        result += f"  Expenses: ${abs(expense):,.2f}\n"
        result += f"  Net Cashflow: ${net:,.2f}\n\n"
    
    return result


# Agent instance following Agent Framework conventions
agent = ChatAgent(
    name="CashflowAnomalyAgent",
    chat_client=AzureAIAgentClient(
        project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
        model_deployment_name=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME"),
        async_credential=AzureCliCredential(),
    ),
    instructions="""
    You are a cashflow analysis assistant specialized in detecting unusual patterns
    and anomalies in financial transactions. You help finance teams identify potential
    issues, irregular spending, or revenue fluctuations.
    
    You have access to tools that can:
    - Summarize cashflow transactions by type (income/expense)
    - Detect anomalies based on deviation thresholds
    - Analyze trends for specific categories
    - Calculate monthly cashflow summaries
    
    When analyzing data, focus on highlighting unusual patterns, significant deviations
    from normal spending/revenue, and provide actionable insights for investigation.
    """,
    tools=[
        get_cashflow_summary,
        detect_anomalies,
        analyze_category_trends,
        get_monthly_cashflow,
    ],
)


def main():
    """Launch the Cashflow Anomaly agent in DevUI."""
    import logging

    from agent_framework.devui import serve

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    logger.info("Starting Cashflow Anomaly Agent")
    logger.info("Available at: http://localhost:8091")
    logger.info("Entity ID: agent_CashflowAnomalyAgent")
    logger.info("Note: Make sure 'az login' has been run for authentication")

    # Launch server with the agent
    serve(entities=[agent], port=8091, auto_open=True)


if __name__ == "__main__":
    main()
