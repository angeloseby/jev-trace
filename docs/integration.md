# Integration Guide — JevTrace for existing agents

## 3-line integration (recommended)

```bash
pip install jev-trace
# for LangChain: pip install jev-trace[langchain]
```

**Any agent:**
```python
from jev_trace import JevTrace
tracer = JevTrace(api_url="http://localhost:8000", task_name="my-agent")
with tracer.span("retriever", inputs={"query": q}):
    docs = retriever(q)
with tracer.span("generator", inputs={"docs": len(docs)}):
    answer = llm.generate(docs)
tracer.complete("completed")  # or "failed"
tracer.analyze()  # triggers Jev (parallel Choice/Score/Noul)
```

`component` accepts aliases: `llm`→`generator`, `search`→`retriever`, `tool`→`tool_router`, `api`→`external_api`, `chain`→`planner` — stored as canonical `planner|retriever|tool_router|memory|generator|verifier|external_api` (`app/schemas/step.py:7`).

View at `http://localhost:3000/runs` → `GET /api/v1/runs/{id}/attribution|graph|recommendations`.

## LangChain / LangGraph

```python
from jev_trace import JevTrace
from jev_trace.langchain import JevTraceCallbackHandler
tracer = JevTrace(api_url="http://localhost:8000")
handler = JevTraceCallbackHandler(tracer)
llm = ChatOpenAI(callbacks=[handler])
chain = prompt | llm | parser
result = chain.invoke({"input": "Find GDP of Brazil"}, config={"callbacks": [handler]})
tracer.complete("completed")
```

For LangGraph `StateGraph`, wrap each node with `tracer.span` (see `scripts/seed.py` for the pattern) or pass the same handler via `config={"callbacks": [handler]}`.

## OTel (zero-code)

Agents already emitting OTel spans:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
OTEL_TRACES_EXPORTER=otlp \
python my_langchain.py
```

Requires `docker compose up otel-collector api` (collector at `infra/otel/otel-collector-config.yaml:1` exports to `POST /api/v1/otlp/traces` `apps/api/app/api/otlp.py:1`). Spans with attribute `component` are mapped (`llm`→`generator`).

## Manual REST (no SDK)

```bash
curl -X POST http://localhost:8000/api/v1/runs -H "Content-Type: application/json" -d '{"task_name":"qa"}'
# → {id}
curl -X POST http://localhost:8000/api/v1/runs/{id}/steps -d '{"step_number":1,"component":"planner","status":"success","latency_ms":80}'
curl -X POST http://localhost:8000/api/v1/runs/{id}/complete -d '{"status":"failed"}'
curl -X POST http://localhost:8000/api/v1/runs/{id}/analyze  # Jev SystemOne
```

Invalid `component` like `llm` now returns `422 {success:false, error:{code:"VALIDATION_ERROR"}, details:{valid_components:[...], hints:{llm:"generator"}}}` (`app/main.py:44`).

## Publishing jev-trace to PyPI

```bash
cd packages/tracer
python -m build
twine upload dist/*
# version in packages/tracer/pyproject.toml:1
```
