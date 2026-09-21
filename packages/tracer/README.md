# jev-trace — 3-line agent integration

```bash
pip install jev-trace
# or: pip install jev-trace[langchain]
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
tracer.analyze()  # triggers Jev (needs JEV_API_KEY on server)
```

**LangChain / LangGraph:**
```python
from jev_trace import JevTrace
from jev_trace.langchain import JevTraceCallbackHandler
tracer = JevTrace(api_url="http://localhost:8000")
handler = JevTraceCallbackHandler(tracer)
llm = ChatOpenAI(callbacks=[handler])
chain = prompt | llm | parser
result = chain.invoke({"input": "…"}, config={"callbacks": [handler]})
tracer.complete("completed")
```

**OTel (zero code):** Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318` and run `docker compose up otel-collector api` — spans with `component` attribute auto-mapped (`llm→generator`, `search→retriever`) via `apps/api/app/api/otlp.py`.

Valid components: `planner, retriever, tool_router, memory, generator, verifier, external_api` — SDK accepts aliases (`llm`, `search`, `tool`, `api`, `chain`) and maps them.
