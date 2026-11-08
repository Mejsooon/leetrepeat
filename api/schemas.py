"""Kształt danych przychodzących z frontendu (walidacja Pydantic)."""
from typing import Literal

from pydantic import BaseModel, Field


class TestIn(BaseModel):
    input: str
    expected: str


class TaskIn(BaseModel):
    title: str = Field(min_length=1)
    language: Literal["python", "csharp"]
    kind: Literal["function", "program"]
    description: str = Field(min_length=1)
    starter_code: str = ""
    hint: str = ""
    solution: str = Field(min_length=1)
    tests: list[TestIn] = Field(min_length=1)


class RunIn(BaseModel):
    language: Literal["python", "csharp"]
    kind: Literal["function", "program"]
    code: str
    tests: list[TestIn] = Field(min_length=1)


class ReviewIn(BaseModel):
    rating: Literal["again", "partial", "good"]
    tests_passed: int | None = None
    tests_total: int | None = None
    hint_used: bool = False
    solution_used: bool = False
