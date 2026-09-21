
# Project: JevTrace — Agent Failure Intelligence Platform

This is the version I'd build if the goal is:

-   Showcase Jev as the core technology
    
-   Solve a real problem
    
-   Have research depth
    
-   Be impressive on a résumé/GitHub
    
-   Be extensible into a startup or paper
    

The idea is inspired by the failure-attribution research (Who&When, Who&When Pro) but expands it into a complete observability and debugging platform. ([GitHub](https://github.com/ag2ai/Agents_Failure_Attribution?utm_source=chatgpt.com "GitHub - ag2ai/Agents_Failure_Attribution: Benchmark for automated failure attributions in agentic systems (🏆 ICML 2025 Spotlight) · GitHub"))

----------

# Problem

Today agent developers can see:

```text
Agent failed.
```

But they still need to manually inspect:

```text
Planner
Retriever
Memory
Tools
Verifier
Generator
```

to figure out:

```text
Who caused it?
When did it become inevitable?
What type of failure happened?
How severe is it?
How do I fix it?
```

Failure attribution has emerged as an active research problem because even strong reasoning models struggle to reliably identify the responsible component and decisive step. ([Ag2ai](https://ag2ai.github.io/Agents_Failure_Attribution/?utm_source=chatgpt.com "Which Agent Causes Task Failures and When? On Automated Failure Attribution of LLM Multi-Agent Systems"))

----------

# Product Vision

Imagine LangSmith + Datadog + Jev.

```text
Agent Run
     ↓
Trace Collector
     ↓
Jev Attribution Engine
     ↓
Root Cause Analysis
     ↓
Repair Recommendations
     ↓
Dashboard
```

Instead of merely showing logs:

```text
Run #847 failed
```

the system says:

```text
Responsible Component:
Retriever (91%)

Decisive Step:
14

Failure Type:
Retrieval Error

Severity:
Critical

Recommended Fix:
Add reranker
```

----------

# Core Innovation

Most observability platforms answer:

```text
What happened?
```

JevTrace answers:

```text
Why did it happen?
```

using dozens of structured Jev decisions.

----------

# System Architecture

```text
                ┌─────────────┐
                │ AI Agent    │
                └──────┬──────┘
                       │
                       ▼
              ┌────────────────┐
              │ Trace Collector │
              └──────┬─────────┘
                     │
                     ▼
              ┌────────────────┐
              │ Trace Store    │
              └──────┬─────────┘
                     │
                     ▼
            ┌────────────────────┐
            │ Trace Processor    │
            └──────┬─────────────┘
                   │
                   ▼
           ┌───────────────────────┐
           │ Jev Attribution Engine│
           └──────┬────────────────┘
                  │
      ┌───────────┼────────────┐
      ▼           ▼            ▼
 Component    Failure      Severity
 Detector     Category      Score

      └───────────┬────────────┘
                  ▼
          Root Cause Engine
                  ▼
          Repair Generator
                  ▼
             Dashboard
```

----------

# Why Jev Is Perfect Here

Jev works through three primitives:

-   Choice
    
-   Score
    
-   Noul
    

and is specifically designed for typed decisions instead of text generation. ([System One Models](https://systemonemodels.org/?utm_source=chatgpt.com "System One Models: the independent hub for AI decision models"))

We'll use all three.

----------

# Data Model

## Run

```json
{
  "run_id": "123",
  "status": "failed",
  "duration": 43
}
```

----------

## Step

```json
{
  "step_id": 14,
  "component": "retriever",
  "status": "success",
  "latency_ms": 280
}
```

----------

## Component Types

```json
[
  "planner",
  "retriever",
  "tool_router",
  "memory",
  "generator",
  "verifier",
  "external_api"
]
```

----------

# Jev Decision Layer

## Decision 1 — Responsible Component

Choice Question

```json
{
  "responsible_component": {
    "type": "choice"
  }
}
```

Options:

```text
planner
retriever
memory
tool_router
generator
verifier
api
```

Output:

```json
{
  "choice": "retriever",
  "confidence": 0.91
}
```

----------

## Decision 2 — Failure Category

Choice

Options:

```text
retrieval_error
planning_error
tool_failure
hallucination
memory_failure
timeout
verification_failure
```

Output:

```json
{
  "choice": "retrieval_error",
  "confidence": 0.87
}
```

----------

## Decision 3 — Severity

Score

Rubric:

```text
Low
Medium
High
Critical
```

Output:

```json
{
  "score": 2.8
}
```

This aligns directly with Jev's Score primitive. ([Jev Agent](https://jev-agent.com/api-reference?utm_source=chatgpt.com "Jev API reference — /v1/systemone, Choice, Score & Noul | Jev Agent"))

----------

## Decision 4 — Causal Hypotheses

Noul

Ask many questions:

```text
Did retrieval cause failure?
Did planning cause failure?
Did tool execution cause failure?
```

Output:

```json
{
  "retrieval_caused_failure": 0.93,
  "planning_caused_failure": 0.11,
  "tool_failure_caused_failure": 0.08
}
```

This creates a probability graph rather than a single label.

----------

# Attribution Graph

Instead of:

```text
Root Cause = Retriever
```

Build:

```text
Planner      0.12
   │
Retriever    0.93
   │
Generator    0.27
```

Now engineers see:

```text
Primary Cause
Secondary Causes
Contributing Factors
```

This is more useful than a binary answer.

----------

# Repair Recommendation Engine

Another Jev Choice question.

Options:

```text
increase_top_k
add_reranker
improve_embeddings
enable_citations
retry_api
add_human_review
```

Output:

```json
{
  "choice": "add_reranker",
  "confidence": 0.84
}
```

----------

# Dashboard Pages

## Run Explorer

```text
Run 847
Status: Failed

Component:
Retriever

Failure:
Retrieval Error

Confidence:
91%
```

----------

## Failure Analytics

```text
Last 30 Days

Retrieval Errors 42%
Planning Errors 23%
Tool Failures 19%
Memory Errors 11%
Other 5%
```

----------

## Component Health

```text
Planner      98%
Retriever    76%
Memory       93%
Generator    89%
```

----------

# Phase Roadmap

## Phase 1 (2 weeks)

Trace collection

Stack:

```text
FastAPI
Postgres
OpenTelemetry
```

Goal:

Store traces.

----------

## Phase 2 (2 weeks)

Jev integration.

Implement:

```text
Who?
What?
Severity?
```

using Choice and Score.

----------

## Phase 3 (2 weeks)

Attribution graph.

Implement:

```text
20+ Noul questions
```

for causal reasoning.

----------

## Phase 4 (3 weeks)

Dashboard.

```text
Next.js
Tailwind
Recharts
```

----------

## Phase 5 (4 weeks)

Research mode.

Evaluate on:

-   Who&When
    
-   Who&When Pro
    

These are the standard benchmarks for agent failure attribution. ([GitHub](https://github.com/ag2ai/Agents_Failure_Attribution?utm_source=chatgpt.com "GitHub - ag2ai/Agents_Failure_Attribution: Benchmark for automated failure attributions in agentic systems (🏆 ICML 2025 Spotlight) · GitHub"))

----------

# Stretch Goal (Research-Level)

Build a replay engine.

```text
Failed Trace
      ↓
Replace Step 14
      ↓
Replay Agent
      ↓
Success?
```

If success:

```text
Step 14 caused failure.
```

This moves from correlation to causal attribution, which is one of the major open challenges identified in current failure-attribution research. ([arXiv](https://arxiv.org/abs/2607.09996?utm_source=chatgpt.com "Who&When Pro: Can LLMs Really Attribute Failures in AI Agents?"))

----------

# Final Résumé Description

> Built **JevTrace**, an AI Agent Failure Intelligence Platform that analyzes OpenTelemetry traces from multi-agent systems and uses Jev's Choice, Score, and Noul primitives to identify responsible components, decisive failure steps, failure categories, severity levels, and remediation strategies. Evaluated against the Who&When/Who&When Pro failure-attribution benchmarks and visualized results through an interactive observability dashboard. ([GitHub](https://github.com/ag2ai/Agents_Failure_Attribution?utm_source=chatgpt.com "GitHub - ag2ai/Agents_Failure_Attribution: Benchmark for automated failure attributions in agentic systems (🏆 ICML 2025 Spotlight) · GitHub"))

This gives you a project that is:

-   technically challenging,
    
-   directly aligned with Jev's design,
    
-   connected to current agent-research benchmarks,
    
-   and much more distinctive than another chatbot or RAG application.
    

Shape the Jev-centered MVP

-   Design the end-to-end build plan
# JevTrace: Complete Implementation Plan (Zero → Hero)

## Goal

Build a production-style platform that:

1.  Collects agent traces
    
2.  Detects failed runs
    
3.  Uses **Jev** as the attribution engine
    
4.  Identifies:
    
    -   Responsible component (Who)
        
    -   Decisive failure step (When)
        
    -   Failure category (What)
        
    -   Severity
        
    -   Repair recommendation
        
5.  Visualizes failures through a dashboard
    

This directly aligns with the failure-attribution problem studied by Who&When Pro and the way Jev is designed to answer multiple typed questions over the same state. ([Who&When Pro](https://whowhenpro.github.io/?utm_source=chatgpt.com "Who&When Pro — Can LLMs Really Attribute Failures in AI Agents?"))

----------

# Phase 0 — Repository Setup

## Monorepo Structure

```text
jevtrace/
│
├── apps/
│   ├── api/
│   ├── dashboard/
│   └── worker/
│
├── packages/
│   ├── attribution/
│   ├── trace-parser/
│   ├── jev-client/
│   ├── schemas/
│   └── analytics/
│
├── infra/
│   ├── docker/
│   ├── terraform/
│   └── k8s/
│
├── tests/
│
├── docs/
│
└── scripts/
```

----------

# Tech Stack

## Backend

```text
FastAPI
SQLAlchemy
PostgreSQL
Redis
Celery
```

## Frontend

```text
Next.js
TypeScript
Tailwind
Recharts
```

## Observability

```text
OpenTelemetry
Grafana
Prometheus
```

## AI

```text
Jev
```

Jev's API uses a single `/v1/systemone` endpoint that accepts a state plus multiple Choice, Score, and Noul questions evaluated in parallel. ([Jev Agent](https://jev-agent.com/api-reference?utm_source=chatgpt.com "Jev API reference — /v1/systemone, Choice, Score & Noul | Jev Agent"))

----------

# Phase 1 — Trace Collection

## Objective

Capture every agent execution step.

----------

## Trace Schema

### Run

```sql
CREATE TABLE runs (
    id UUID PRIMARY KEY,
    status VARCHAR(20),
    task_name TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP
);
```

----------

### Step

```sql
CREATE TABLE steps (
    id UUID PRIMARY KEY,
    run_id UUID,
    step_number INT,

    component VARCHAR(50),

    input JSONB,
    output JSONB,

    status VARCHAR(20),

    latency_ms INT,

    created_at TIMESTAMP
);
```

----------

### Components

```text
planner
retriever
tool_router
generator
memory
verifier
external_api
```

These map well to the attribution dimensions used in current benchmarks. ([GitHub](https://github.com/ag2ai/whowhen_pro/blob/main/README.md?utm_source=chatgpt.com "whowhen_pro/README.md at main · ag2ai/whowhen_pro · GitHub"))

----------

## API

### Create Run

```http
POST /runs
```

Response:

```json
{
  "run_id": "uuid"
}
```

----------

### Add Step

```http
POST /runs/{id}/steps
```

```json
{
  "component": "retriever",
  "status": "success",
  "latency_ms": 250
}
```

----------

### End Run

```http
POST /runs/{id}/complete
```

----------

# Phase 2 — Failure Detection

## Goal

Decide:

```text
Success?
Failure?
```

----------

## Failure Table

```sql
CREATE TABLE failures (
    id UUID PRIMARY KEY,
    run_id UUID,

    failure_detected BOOLEAN,

    reason TEXT,

    severity_score FLOAT
);
```

----------

## Detection Sources

### Rule Based

```python
if timeout:
    failure = True
```

### LLM Evaluator

```text
Did the answer satisfy the task?
```

### Human Labels

```text
PASS / FAIL
```

----------

# Phase 3 — Trace Normalization

Raw traces are messy.

Convert:

```text
Planner
Search
Retriever
Generator
```

into a compact state.

----------

## Example State

```json
{
  "task": "Find GDP of Brazil",

  "steps": [
    {
      "component": "planner",
      "status": "success"
    },
    {
      "component": "retriever",
      "status": "success"
    },
    {
      "component": "generator",
      "status": "failed"
    }
  ]
}
```

This becomes the Jev input state.

----------

# Phase 4 — Jev Attribution Engine

This is the core project.

Jev excels at typed questions:

-   Choice
    
-   Score
    
-   Noul
    

evaluated simultaneously against the same state. ([Jev Agent](https://jev-agent.com/api-reference?utm_source=chatgpt.com "Jev API reference — /v1/systemone, Choice, Score & Noul | Jev Agent"))

----------

## Attribution Service

```text
Trace
 ↓
Normalizer
 ↓
Jev
 ↓
Attribution
```

----------

# Question Set 1

## Responsible Component

Choice

```json
{
  "responsible_component": {
    "type": "choice"
  }
}
```

Options:

```text
planner
retriever
tool_router
memory
generator
verifier
external_api
```

----------

# Question Set 2

## Failure Category

Choice

```text
planning_error
retrieval_error
tool_failure
memory_failure
hallucination
timeout
verification_failure
```

These categories should be inspired by the broader failure taxonomies in Who&When Pro. ([Who&When Pro](https://whowhenpro.github.io/?utm_source=chatgpt.com "Who&When Pro — Can LLMs Really Attribute Failures in AI Agents?"))

----------

# Question Set 3

## Severity

Score

Rubric:

```text
Low
Medium
High
Critical
```

----------

# Question Set 4

## Causal Hypotheses

Multiple Noul questions.

```text
Did retrieval cause failure?
Did planning cause failure?
Did memory cause failure?
Did tool execution cause failure?
```

Output:

```json
{
  "retrieval_caused_failure": 0.91,
  "planning_caused_failure": 0.12
}
```

----------

# Attribution Database

```sql
CREATE TABLE attributions (
    id UUID PRIMARY KEY,

    run_id UUID,

    responsible_component VARCHAR(50),

    component_confidence FLOAT,

    failure_step INT,

    failure_category VARCHAR(50),

    category_confidence FLOAT,

    severity FLOAT,

    created_at TIMESTAMP
);
```

----------

# Phase 5 — Failure Attribution Graph

This becomes your differentiator.

Instead of:

```text
Retriever caused failure
```

Store:

```json
{
  "planner": 0.14,
  "retriever": 0.91,
  "generator": 0.31
}
```

Graph:

```text
Planner      0.14
     │
Retriever    0.91
     │
Generator    0.31
```

----------

# Phase 6 — Repair Recommendation Engine

Second Jev call.

Question:

```text
Best remediation?
```

Choices:

```text
increase_top_k
add_reranker
improve_embeddings
retry_api
enable_citations
human_review
```

Store:

```sql
CREATE TABLE recommendations (
    id UUID PRIMARY KEY,

    run_id UUID,

    recommendation TEXT,

    confidence FLOAT
);
```

----------

# Phase 7 — Analytics

## Failure Trends

```sql
SELECT
failure_category,
COUNT(*)
FROM attributions
GROUP BY failure_category;
```

Dashboard:

```text
Retrieval Errors 42%
Planning Errors 21%
Tool Failures 18%
```

----------

## Component Reliability

```text
Planner      97%
Retriever    74%
Generator    88%
```

----------

# Phase 8 — Dashboard

## Page 1

### Runs

```text
Run ID
Status
Duration
```

----------

## Page 2

### Trace Explorer

```text
Step 1
Step 2
Step 3
```

Open any step.

See:

```text
Input
Output
Latency
```

----------

## Page 3

### Attribution

```text
Responsible Component:
Retriever

Confidence:
91%

Failure Category:
Retrieval Error
```

----------

## Page 4

### Attribution Graph

Interactive DAG.

```text
Planner
  ↓
Retriever
  ↓
Generator
```

Colored by probability.

----------

# Phase 9 — Benchmarking

Use:

### Who&When Pro

Measures:

```text
Who?
When?
Error Mode?
Joint Accuracy?
```

and contains over 12,000 labeled failed trajectories. ([GitHub](https://github.com/ag2ai/whowhen_pro/blob/main/README.md?utm_source=chatgpt.com "whowhen_pro/README.md at main · ag2ai/whowhen_pro · GitHub"))

----------

## Evaluation Metrics

```text
Who Accuracy
When Accuracy
Error F1
Joint Accuracy
```

These are the benchmark's core metrics. ([GitHub](https://github.com/ag2ai/whowhen_pro/blob/main/README.md?utm_source=chatgpt.com "whowhen_pro/README.md at main · ag2ai/whowhen_pro · GitHub"))

----------

# Testing Strategy

## Unit Tests

```text
Normalizer
Jev Client
Feature Builder
Recommendation Engine
```

Target:

```text
>90% coverage
```

----------

## Integration Tests

```text
API → DB
API → Jev
Worker → DB
```

Mock Jev responses.

----------

## End-to-End Tests

Scenario:

```text
Run Agent
Collect Trace
Fail
Analyze
Render Dashboard
```

Verify:

```text
Expected Attribution Returned
```

----------

# CI/CD

## GitHub Actions

Pipeline:

```text
Lint
Unit Tests
Integration Tests
Build Docker
Push Image
Deploy
```

----------

# Deployment

## Local

```bash
docker compose up
```

Services:

```text
api
worker
postgres
redis
dashboard
```

----------

## Cloud

### Backend

```text
Fly.io
Railway
Render
AWS ECS
```

### Database

```text
Neon
Supabase
RDS
```

### Frontend

```text
Vercel
```

----------

# Milestones

### Milestone 1 (Week 1-2)

-   Repository setup
    
-   DB schema
    
-   Trace ingestion API
    

### Milestone 2 (Week 3-4)

-   Failure detection
    
-   Trace explorer
    

### Milestone 3 (Week 5-6)

-   Jev integration
    
-   Component attribution
    

### Milestone 4 (Week 7-8)

-   Failure categories
    
-   Severity scoring
    
-   Recommendations
    

### Milestone 5 (Week 9-10)

-   Attribution graph
    
-   Analytics dashboard
    

### Milestone 6 (Week 11-12)

-   Benchmark on Who&When Pro
    
-   CI/CD
    
-   Production deployment
    

### Milestone 7 (Stretch)

-   Counterfactual replay engine
    
-   Automatic remediation validation
    
-   Self-improving agent feedback loop
    

The strongest version of JevTrace uses Jev exactly the way its API is intended: one trace state, many parallel Choice/Score/Noul decisions, producing a structured attribution graph rather than a single generated explanation. ([Jev Agent](https://jev-agent.com/api-reference?utm_source=chatgpt.com "Jev API reference — /v1/systemone, Choice, Score & Noul | Jev Agent"))

Continue with the implementation blueprint

-   Define the API contracts and request/response schemas
# JevTrace API Specification v1

This is the API contract I'd freeze before writing any code.

----------

# API Design Principles

### Resource-oriented

```http
/runs
/steps
/attributions
/recommendations
/auth
```

### Versioned

```http
/api/v1/*
```

### JSON only

```http
Content-Type: application/json
```

### JWT Authentication

```http
Authorization: Bearer <token>
```

### Cursor Pagination

Prefer cursor pagination over offset for large trace datasets.

----------

# Authentication

## Login

### Request

```http
POST /api/v1/auth/login
```

```json
{
  "email": "angelo@example.com",
  "password": "secret"
}
```

### Response

```json
{
  "access_token": "jwt-token",
  "refresh_token": "refresh-token",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

----------

## Refresh Token

```http
POST /api/v1/auth/refresh
```

```json
{
  "refresh_token": "..."
}
```

### Response

```json
{
  "access_token": "new-token",
  "expires_in": 3600
}
```

----------

# Common Models

## Base Response

```python
class ApiResponse(BaseModel):
    success: bool
    data: Any | None
    error: ErrorResponse | None
```

----------

## Error Response

```python
class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | None = None
```

Example:

```json
{
  "success": false,
  "error": {
    "code": "RUN_NOT_FOUND",
    "message": "Run does not exist"
  }
}
```

FastAPI supports strongly typed response models and additional error response schemas through Pydantic/OpenAPI definitions. ([FastAPI](https://fastapi.tiangolo.com/tutorial/response-model/?utm_source=chatgpt.com "Response Model - Return Type - FastAPI"))

----------

# Pagination

## Request

```http
GET /runs?limit=20&cursor=eyJpZCI6...
```

## Response

```python
class CursorPage(BaseModel):
    items: list[Any]
    next_cursor: str | None
    has_more: bool
```

Example:

```json
{
  "items": [...],
  "next_cursor": "eyJpZCI6...",
  "has_more": true
}
```

----------

# Domain Models

## Run

```python
class RunStatus(str, Enum):
    running = "running"
    completed = "completed"
    failed = "failed"
```

```python
class Run(BaseModel):
    id: UUID
    task_name: str
    status: RunStatus

    started_at: datetime
    ended_at: datetime | None

    total_steps: int
```

----------

## Step

```python
class Step(BaseModel):
    id: UUID
    run_id: UUID

    step_number: int

    component: str

    status: str

    input: dict
    output: dict

    latency_ms: int

    created_at: datetime
```

----------

## Attribution

```python
class Attribution(BaseModel):
    run_id: UUID

    responsible_component: str

    component_confidence: float

    failure_step: int

    failure_category: str

    category_confidence: float

    severity: float
```

----------

## Recommendation

```python
class Recommendation(BaseModel):
    recommendation: str
    confidence: float
```

----------

# Run APIs

----------

## Create Run

### Route

```http
POST /api/v1/runs
```

### Request

```json
{
  "task_name": "answer_question"
}
```

### Response

```json
{
  "id": "e12c...",
  "status": "running",
  "started_at": "2026-09-21T10:00:00Z"
}
```

----------

## List Runs

### Route

```http
GET /api/v1/runs
```

### Query Parameters

```http
?status=failed
?limit=20
?cursor=...
```

### Response

```json
{
  "items": [
    {
      "id": "123",
      "status": "failed"
    }
  ],
  "next_cursor": "abc",
  "has_more": true
}
```

----------

## Get Run

### Route

```http
GET /api/v1/runs/{run_id}
```

### Response

```json
{
  "id": "123",
  "task_name": "qa",
  "status": "failed",
  "total_steps": 12
}
```

----------

## Complete Run

### Route

```http
POST /api/v1/runs/{run_id}/complete
```

### Request

```json
{
  "status": "failed"
}
```

### Response

```json
{
  "success": true
}
```

----------

# Step APIs

----------

## Add Step

### Route

```http
POST /api/v1/runs/{run_id}/steps
```

### Request

```json
{
  "step_number": 4,

  "component": "retriever",

  "status": "success",

  "input": {
    "query": "GDP Brazil"
  },

  "output": {
    "documents": 5
  },

  "latency_ms": 280
}
```

### Response

```json
{
  "id": "step-uuid"
}
```

----------

## List Steps

### Route

```http
GET /api/v1/runs/{run_id}/steps
```

### Response

```json
{
  "items": [
    {
      "step_number": 1,
      "component": "planner"
    }
  ]
}
```

----------

## Get Step

### Route

```http
GET /api/v1/steps/{step_id}
```

----------

# Attribution APIs

These are Jev-powered.

----------

## Analyze Run

### Route

```http
POST /api/v1/runs/{run_id}/analyze
```

### Flow

```text
Trace
 ↓
Normalizer
 ↓
Jev
 ↓
Attribution
```

----------

### Response

```json
{
  "run_id": "123",

  "responsible_component": {
    "name": "retriever",
    "confidence": 0.91
  },

  "failure_step": {
    "step_number": 14,
    "confidence": 0.87
  },

  "failure_category": {
    "name": "retrieval_error",
    "confidence": 0.88
  },

  "severity": 0.92
}
```

----------

## Get Attribution

### Route

```http
GET /api/v1/runs/{run_id}/attribution
```

### Response

```json
{
  "responsible_component": "retriever",
  "component_confidence": 0.91,

  "failure_step": 14,

  "failure_category": "retrieval_error",

  "severity": 0.92
}
```

----------

# Attribution Graph API

This is the differentiator.

----------

## Get Attribution Graph

### Route

```http
GET /api/v1/runs/{run_id}/graph
```

### Response

```json
{
  "nodes": [
    {
      "id": "planner",
      "weight": 0.12
    },
    {
      "id": "retriever",
      "weight": 0.91
    }
  ],

  "edges": [
    {
      "source": "planner",
      "target": "retriever"
    }
  ]
}
```

----------

# Recommendation APIs

----------

## Generate Recommendations

### Route

```http
POST /api/v1/runs/{run_id}/recommendations
```

### Response

```json
{
  "recommendations": [
    {
      "action": "add_reranker",
      "confidence": 0.84
    },
    {
      "action": "increase_top_k",
      "confidence": 0.71
    }
  ]
}
```

----------

## Get Recommendations

```http
GET /api/v1/runs/{run_id}/recommendations
```

----------

# Analytics APIs

----------

## Failure Distribution

### Route

```http
GET /api/v1/analytics/failures
```

### Response

```json
{
  "retrieval_error": 42,
  "planning_error": 21,
  "tool_failure": 18
}
```

----------

## Component Reliability

### Route

```http
GET /api/v1/analytics/components
```

### Response

```json
{
  "planner": 0.97,
  "retriever": 0.74,
  "generator": 0.89
}
```

----------

## Trend Data

### Route

```http
GET /api/v1/analytics/trends?days=30
```

### Response

```json
{
  "series": [
    {
      "date": "2026-09-01",
      "failures": 12
    }
  ]
}
```

----------

# Internal Jev Service API

The dashboard should never call Jev directly.

Create an internal service:

```http
POST /internal/jev/analyze
```

Input:

```json
{
  "normalized_trace": {...}
}
```

Output:

```json
{
  "responsible_component": "retriever",

  "failure_category": "retrieval_error",

  "severity": 0.91,

  "causal_hypotheses": {
    "retrieval": 0.91,
    "planning": 0.11
  }
}
```

----------

# Standard HTTP Status Codes

Code

Meaning

200

Success

201

Created

202

Analysis queued

400

Validation error

401

Unauthorized

403

Forbidden

404

Not found

409

Conflict

422

Invalid payload

429

Rate limited

500

Internal error

FastAPI can document and validate both success and error responses through Pydantic response models and OpenAPI response definitions. ([FastAPI](https://fastapi.tiangolo.com/tutorial/response-model/?utm_source=chatgpt.com "Response Model - Return Type - FastAPI"))

# Recommended FastAPI Router Layout

```text
app/
├── api/
│   ├── auth.py
│   ├── runs.py
│   ├── steps.py
│   ├── attributions.py
│   ├── recommendations.py
│   └── analytics.py
│
├── schemas/
│   ├── auth.py
│   ├── run.py
│   ├── step.py
│   ├── attribution.py
│   ├── recommendation.py
│   └── common.py
│
├── services/
│   ├── jev_service.py
│   ├── attribution_service.py
│   ├── analytics_service.py
│   └── recommendation_service.py
│
└── db/
    ├── models.py
    └── session.py
```

This contract is sufficiently complete to start backend implementation, generate OpenAPI docs automatically, build the frontend in parallel, and later swap a mock attribution engine for the real Jev integration without changing public APIs.

Continue the API design

-   Add the FastAPI implementation skeleton
    
-   Define the OpenAPI security and error schemas
