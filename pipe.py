"""
title: Financial Extractor Pipe
date: 3-9-2025
version: 1.0.0
description: A pipe that processes extracted document through multiple sequential custom models
"""

from typing import Union, Generator, Iterator
import os
from fastapi import Request
from pydantic import BaseModel, Field
from open_webui.main import chat_completion


class User(BaseModel):
    """
    Represents a user interacting with the system.
    """

    id: str
    email: str
    name: str
    role: str


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

    async def pipe(
        self, body: dict, __user__: dict, __request__: Request
    ) -> Union[str, Generator, Iterator]:

        user = User(**__user__)

        try:
            markdown_content = body["messages"][-1]["content"]
            balance_sheet_result = await self.process_with_custom_model(
                body,
                markdown_content,
                self.valves.LLM_BSE_ID,
                "Balance Sheet",
                __request__,
                user,
            )
            income_statement_result = await self.process_with_custom_model(
                body,
                markdown_content,
                self.valves.LLM_ISE_ID,
                "Income Statement",
                __request__,
                user,
            )
            cash_flow_statement_result = await self.process_with_custom_model(
                body,
                markdown_content,
                self.valves.LLM_CFSE_ID,
                "Cash Flow Statement",
                __request__,
                user,
            )

            final_response = self.format_combined_response(
                balance_sheet_result,
                income_statement_result,
                cash_flow_statement_result,
            )
            return final_response

        except Exception as e:
            return f"Error in pipe: {str(e)}"

    async def process_with_custom_model(
        self,
        body: dict,
        markdown_content: str,
        model_id: str,
        model_name: str,
        request: Request,
        user: User,
    ):
        if not model_id:
            return f"{model_name}: Model ID not configured"
        try:
            body["messages"].append(
                {
                    "role": "user",
                    "content": f"Extract {model_name}:\n\n{markdown_content}",
                }
            )
            payload = {**body, "model": model_id}
            return await chat_completion(request, payload, user)
        except Exception as e:
            return f"{model_name}: Processing failed - {str(e)}"

    def format_combined_response(
        self,
        balance_sheet_result: str,
        income_statement_result: str,
        cash_flow_statement_result: str,
    ):
        response = f"""### Financial Statement

{balance_sheet_result["choices"][0]["message"]["content"]}
{income_statement_result["choices"][0]["message"]["content"]}
{cash_flow_statement_result["choices"][0]["message"]["content"]}

---

*Extraction completed successfully*  
Please recheck to ensure extraction accuracy.
"""
        return response
