#!/usr/bin/env python3

print("Starting test")

from fastapi import Query, Request, Depends
from typing import Optional

print("Imports successful")

def test_func(request: Request = Depends(), query_token: str = Query(None, alias="token")) -> str:
    return "test"

print("Function defined successfully")

print("Test completed") 