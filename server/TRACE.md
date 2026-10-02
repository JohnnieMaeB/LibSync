# LibSync Server — Execution Trace

Two diagrams: what runs at import time, and the call chain from each HTTP endpoint down through routers,
the agent, its tools, the backing services, and the external systems they call. See
[ARCHITECTURE.md](../ARCHITECTURE.md) for the *why* — this doc is just *what calls what*.

## Boot sequence

<p align="center">
  <img src="../planning/assets/server-trace-boot.svg" alt="Diagram of the LibSync backend's import-time boot sequence: config.py loads .env, rate_limit.py builds the limiter, bot_context files (persona + service principles) feed agent.py, which builds the three-Groq-model-then-HF fallback chain and registers four tools, then session_store and services load, routers load, main.py assembles the FastAPI app and mounts routers, and finally at serve time lifespan opens the shared httpx client." width="900" />
</p>

## Runtime call graph

<p align="center">
  <img src="../planning/assets/server-trace-callgraph.svg" alt="Runtime call graph of the LibSync backend from each of its five HTTP endpoints down through router handlers, the session store, the PydanticAI agent's run methods, the shared tool-calling loop with its four tools, the five backing services, and the five external systems they call." width="1100" />
</p>

The two dashed side paths (`citation_style_switch()` and `query()`) are the only routes that skip the
LLM/tool-calling loop entirely — everything else funnels through the one shared `chat_agent`.

---

## Symbol index

The diagrams show every file and every *entry point*; they don't have room for every private helper. This
is the rest, one line per symbol, grouped by file.

**`app/main.py`** — `lifespan(app)` opens/closes the shared `httpx.AsyncClient`; `rate_limit_handler(request, exc)` returns 429 JSON.

**`app/config.py`** — no functions, just `load_dotenv` + env var reads at import time.

**`app/deps.py`** — `LibSyncDeps(http_client, library_id=None)`: the shared `httpx.AsyncClient`, plus the embedding library's validated id (Tier 8 groundwork), injected into every tool via `RunContext`.

**`app/tenants.py`** — `normalize_library_id(raw)` validates the `X-LibSync-Library` header as a lowercase slug (anything else → `None`, so a crafted header can't pick a namespace); `policy_namespace(library_id)` returns the library's own Pinecone namespace once one exists, else `pinecone_service.DEFAULT_NAMESPACE` (`ns1`); `_known_namespaces()` caches the index's namespace list for 5 minutes.

**`app/rate_limit.py`** — `limiter` (per-IP, `RATE_LIMIT`) plus `get_origin_or_ip(request)`, the key function behind `WIDGET_ORIGIN_RATE_LIMIT`, stacked as a second decorator on `/agent` and `/chat*` so one embedding origin can't drain the shared free-tier budget (Tier 6).

**`app/widget_registry.py`** — `WidgetRegistry.register/is_registered/consume_grace`, an in-memory library-id → origin allowlist; `check_widget_registration(library_id, origin)` lets unregistered widget origins use a 50-request grace quota before requiring `POST /widget/register` (`app/routers/widget.py`).

**`app/session_store.py`** — `SessionStore.get/append/_evict_expired/_evict_oldest_if_full`; one shared `session_store` instance, same class for both transports (only the key differs: client-minted `session_id` vs. AG-UI `thread_id`).

**`app/schemas.py`** — `Book`, `BookResult`, `ScholarlyWork`, `ResearchResult`, `Citation`, `QueryRequest`; every model here is referenced by a route (the five that weren't — `ChatRequest`, `ChatResponse`, `ErrorResponse`, `QueryMatch`, `QueryResponse` — were removed).

**`app/agent.py`** (beyond what's in the diagram) — `_custom_event(name, value) -> CustomEvent`, the helper every tool uses to attach a card payload to `ToolReturn.metadata`; `_reject_leaked_tool_call_syntax(data)`, the output validator that retries a turn if the model leaks raw tool-call syntax into text; `_search_policies(query, library_id)`, which resolves the library's namespace and searches Pinecone in one worker thread. `chat_agent`'s `metadata=` callable records `library_id` on every run's Logfire span. The model is a `FallbackModel` over `_groq_model` (`openai/gpt-oss-120b`), `_groq_qwen_model`, `_groq_small_model` and `_huggingface_model` — each Groq model is a separate free-tier daily token quota.

**`app/routers/agent.py`** — `_run_stream_with_retry(adapter, ...)` retries a whole turn that fails before any content streams; `_patron_safe(event)` replaces a `RUN_ERROR`'s raw provider text with `PATRON_ERROR_MESSAGE` and logs the original; `_persist(result)`, the closure that saves both the frontend's new turn *and* `result.new_messages()` to `session_store` (both are needed — `new_messages()` alone silently drops the user's own message every turn, a real bug fixed during Tier 2).

**`app/routers/chat.py`** — `_parse_chat_request(request)` manually parses the JSON body and mints a `session_id` if none was sent; `_format_sse(event, data)` formats the old `event: .../data: ...` frame; `_has_json_body(request)`.

**`app/services/pinecone_service.py`** — `search_pinecone(text, top_k, namespace=DEFAULT_NAMESPACE)`; `list_namespaces()` (used by `tenants.py`); `_get_index()` lazily constructs the `Pinecone` client on first call — deliberately, not just deferred-for-convenience: `PINECONE_API_KEY` has no safe placeholder default the way `GROQ_API_KEY`/`HUGGINGFACE_TOKEN` do, and `Pinecone(api_key=None)` raises immediately, so building it eagerly at import time would break importing `app.main` (and every test) in any environment without a real Pinecone key.

**`app/services/open_library_service.py`** — `_availability_from_search_doc(doc)`, `_check_availability(client, edition_olid)` (returns `"unknown"` on any failure rather than propagating).

**`app/services/openalex_service.py`** — `_reconstruct_abstract(inverted_index)` rebuilds plain text from OpenAlex's word→position index.

**`app/services/citation_service.py`** — `crossref_to_csl_json(work)` maps Crossref → CSL-JSON, **omitting** absent optional fields rather than setting `None` (citeproc-py renders a `None` field literally, e.g. `"(None)"`).

**Outside the request path: `evals/`** — `evals/task.py`'s `make_task(http_client)` runs one (possibly multi-turn) conversation through `chat_agent` and returns the reply plus `tools_called(messages)`; `_run_turn` waits out per-minute 429s and fails fast on daily-quota ones. `evals/run.py`'s `main()` evaluates `evals/dataset.py`'s cases, by default against `_groq_model` alone (`--with-fallback` for the full chain). See [`evals/README.md`](evals/README.md).

---

## Worth knowing

Three things this trace surfaced, now resolved:

- **5 dead schemas** in `schemas.py` were never referenced by any route — removed (`ChatRequest`,
  `ChatResponse`, `ErrorResponse`, `QueryMatch`, `QueryResponse`).
- **`POST /api/query` blocked the event loop** during its Pinecone call while the equivalent tool
  (`search_library_policies`) offloaded the same call to a thread — `query()` now does the same via
  `anyio.to_thread.run_sync`, matching the tool's pattern.
- **`_pinecone_client`'s lazy construction turned out to be load-bearing, not an inconsistency to fix.**
  `Pinecone(api_key=None)` raises immediately, and `PINECONE_API_KEY` (unlike `GROQ_API_KEY`/
  `HUGGINGFACE_TOKEN`) has no `"unset"`-style placeholder fallback — verified live: `Pinecone(api_key=None)`
  does in fact raise `PineconeValueError` on construction. Making this eager would break importing
  `app.main` in any environment without a real Pinecone key, so it stays lazy; the reasoning is now a
  comment on `_get_index()` instead of an unexplained inconsistency.
