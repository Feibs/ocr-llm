"""
title: Financial Extractor Pipe
date: 12-08-2025
version: 1.0.0
description: A pipe that processes extracted document through multiple sequential custom models
"""

from typing import List, Union, Generator, Iterator
import os
import base64
import requests
import pathlib
from pydantic import BaseModel, Field


class Pipe:
    class Valves(BaseModel):
        """Configuration for Financial Extractor Pipe"""

        LLM_API_ENDPOINT: str = Field(default="")
        LLM_API_KEY: str = Field(default="")
        LLM_BSE_ID: str = Field(default="balance-sheet")
        LLM_ISE_ID: str = Field(default="income-statement")
        LLM_CFSE_ID: str = Field(default="cash-flow-statement")

    def __init__(self):
        self.valves = self.Valves(
            **{
                "LLM_API_ENDPOINT": os.getenv("LLM_API_ENDPOINT", ""),
                "LLM_API_KEY": os.getenv("LLM_API_KEY", ""),
                "LLM_BSE_ID": os.getenv("LLM_BSE_ID", "balance-sheet"),
                "LLM_ISE_ID": os.getenv("LLM_ISE_ID", "income-statement"),
                "LLM_CFSE_ID": os.getenv("LLM_CFSE_ID", "cash-flow-statement"),
            }
        )

    def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        try:
            markdown_content = body["messages"][-1]["content"]
            balance_sheet_result = self.process_with_custom_model(
                markdown_content, self.valves.LLM_BSE_ID, "Balance Sheet"
            )
            income_statement_result = self.process_with_custom_model(
                markdown_content, self.valves.LLM_ISE_ID, "Income Statement"
            )
            cash_flow_statement_result = self.process_with_custom_model(
                markdown_content, self.valves.LLM_CFSE_ID, "Cash Flow Statement"
            )

            final_response = self.format_combined_response(
                balance_sheet_result,
                income_statement_result,
                cash_flow_statement_result,
            )
            return final_response

        except Exception as e:
            return f"Error in pipe: {str(e)}"

    def process_with_custom_model(self, markdown_content, model_id, model_name):
        if not model_id:
            return f"{model_name}: Model ID not configured"

        try:
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Extract {model_name}:\n\n{markdown_content}",
                    }
                ],
                "stream": False,
            }

            headers = {
                "Authorization": f"Bearer {self.valves.LLM_API_KEY}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                f"{self.valves.LLM_API_ENDPOINT}/api/chat/completions",
                json=payload,
                headers=headers,
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                return f"{model_name}: Error {response.status_code} - {response.text}"

        except Exception as e:
            return f"{model_name}: Processing failed - {str(e)}"

    def format_combined_response(
        self, balance_sheet_result, income_statement_result, cash_flow_statement_result
    ):
        response = f"""# Financial Statement Extraction Result

## Balance Sheet Extraction
{balance_sheet_result}

## Income Statement Extraction
{income_statement_result}

## Cash Flow Statement Extraction
{cash_flow_statement_result}

---

*Extraction completed successfully*  
Please recheck to ensure extraction accuracy.
"""
        return response
