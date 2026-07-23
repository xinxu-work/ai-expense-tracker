# Hybrid RAG Development Plan

## 1. Objective

Extend the Expense Tracker from a structured-data Foundry agent into a hybrid retrieval-augmented generation (RAG) assistant.

The assistant will use:

- deterministic SQL/API tools for transactions, budgets, savings, and affordability calculations;
- document RAG for unstructured content such as receipts, bank-statement text, budgeting rules, personal finance notes, and expense policies;
- Microsoft Foundry for the agent and response generation;
- Supabase/PostgreSQL for the initial document metadata and vector-storage layer, or Azure AI Search/Databricks Vector Search when the deployment target requires it.

The design goal is grounded, cited answers without allowing the language model to invent financial figures or perform financial calculations.

## 2. Current baseline

The project already provides:

- Supabase PostgreSQL storage with transactions, categories, budgets, savings goals, merchant rules, and pay dates;
- dbt staging and reporting marts for spending, savings, pay periods, and budget-versus-actual analysis;
- FastAPI endpoints, including the deterministic `/advice/can-i-afford` business boundary;
- a Microsoft Foundry function-calling agent with tools for spending, budgets, summaries, categories, transaction search, and purchase affordability;
- initial governance patterns including an `activity_id`, tool separation, audit logging, and a governance roadmap.

The project does not yet contain the production-shaped version of:

- document ingestion or file storage beyond the local Markdown source;
- PDF/text extraction or OCR;
- dense embeddings and a managed vector index;
- document versioning and hash-based refresh logic;
- a full answer-citation and retrieval-evaluation framework.

The first learning slice now provides a dependency-free TF-IDF retriever for
the interview Q&A Markdown file. It is useful for practising ingestion,
question-level chunking, ranking, citations, API integration, and agent
routing. It is not the final dense-embedding/vector-database implementation;
that remains the next production-shaped milestone.

## 3. Target architecture

```text
User
  |
  v
Microsoft Foundry Agent
  |------------------------------|
  v                              v
Structured tools                 RAG retrieval tool
  |                              |
  v                              v
FastAPI + Supabase               Filtered vector search
  |                              |
  v                              v
Transactions, budgets,           Document chunks and metadata
dbt marts, affordability         |
                                 v
                         Retrieved context + citations
                                  |
                                  v
                          Grounded model response
```

### Routing rule

Use structured tools when the question requires an exact value, aggregation, date filter, budget rule, or financial decision. Use RAG when the answer depends on document meaning or explanatory text. Use both when a question combines personal data with a documented rule.

Example:

> “Did I exceed my Dining Out budget, and what does my budgeting note recommend?”

The agent should call the budget-status tool for the first part and retrieve the relevant budgeting note for the second part.

## 4. Delivery phases

### Phase 0 — Scope and acceptance criteria

Deliverables:

- define the first document types to support;
- define supported question types and out-of-scope financial advice;
- create a small representative document set;
- create a golden question-and-answer evaluation set;
- decide whether the first vector store is Supabase/PostgreSQL or a managed Azure/Databricks service.

Exit criteria:

- at least 10 representative documents or document sections;
- at least 20 test questions covering answerable, ambiguous, and unanswerable cases;
- explicit distinction between structured-data questions and document-RAG questions.

### Phase 1 — Document ingestion foundation

Deliverables:

- document upload or local ingestion command;
- file metadata record with source, hash, version, modified time, status, and owner;
- text extraction for text PDFs and Markdown/TXT files;
- page-aware records so citations can identify the source page;
- initial logging for ingestion success, failure, duration, and extracted text size.

Suggested document states:

```text
discovered -> processing -> indexed
                         \-> failed
```

Exit criteria:

- a document can be ingested repeatedly without creating duplicate active versions;
- extraction failures are visible and do not silently create empty embeddings;
- every indexed chunk can be traced back to a source document and page.

### Phase 2 — Chunking, embeddings, and vector retrieval

The current prototype's local TF-IDF index is a baseline for this phase. It
should be replaced or complemented by dense embeddings and a managed or
PostgreSQL vector index once the retrieval contract and evaluation set are
stable.

Deliverables:

- semantic or section-aware chunking with controlled overlap;
- embedding generation using the selected Azure/OpenAI-compatible embedding model;
- vector storage and similarity search;
- metadata filters for owner, document type, source, and version;
- a retrieval function returning chunk text, score, source, page, and document version.

Initial retrieval behavior:

- retrieve a small top-k candidate set;
- filter by access permissions before the model sees the content;
- optionally combine semantic search with keyword search for merchant names and policy terms;
- return no context when relevance is below the configured threshold;
- preserve source metadata for citations.

Exit criteria:

- retrieval returns the expected source section for the golden questions;
- unauthorized document chunks are never returned;
- low-relevance questions produce a controlled “I could not find this in the connected documents” result.

### Phase 3 — Foundry agent integration

Deliverables:

- add a `retrieve_knowledge` tool to the existing tool registry;
- update the agent instructions with routing rules;
- make the model cite document name and page when RAG context is used;
- preserve the existing affordability tool as the only authority for affordability decisions;
- add response handling for missing, conflicting, or stale context.

Recommended tool boundaries:

| Tool | Responsibility | Model allowed to calculate? |
|---|---|---|
| `get_monthly_spending` | Exact spending totals | No; tool returns facts |
| `get_budget_status` | Budget-versus-actual status | No; tool returns facts |
| `check_purchase_affordability` | Deterministic purchase decision | No |
| `search_transactions` | Transaction lookup | No; tool returns records |
| `retrieve_knowledge` | Unstructured document context | No; tool returns evidence |

Exit criteria:

- structured questions continue to use structured tools;
- RAG answers include citations;
- combined questions use both sources when appropriate;
- the agent does not present retrieved policy text as a numerical calculation.

### Phase 4 — Document change detection and re-indexing

Deliverables:

- calculate a content hash for every source file;
- skip re-embedding unchanged files;
- create a new document version when the hash changes;
- deactivate or delete old chunks for the replaced version;
- retain enough metadata to audit which version supported an answer;
- add a scheduled or event-triggered refresh path.

Update flow:

```text
source file changed
        |
        v
compare hash and modified time
        |
        +-- unchanged -> skip
        |
        +-- changed -> extract -> chunk -> embed -> activate new version
                                      |
                                      v
                              deactivate old chunks
```

Exit criteria:

- an updated PDF is reflected in retrieval;
- unchanged documents do not incur embedding work;
- old versions remain auditable but are not retrieved by default.

### Phase 5 — Evaluation and production governance

Deliverables:

- retrieval evaluation: recall@k, precision of returned context, and citation correctness;
- answer evaluation: groundedness, completeness, refusal quality, and numerical accuracy;
- latency and cost measurements for ingestion, retrieval, and generation;
- prompt and embedding-model version tracking;
- audit events containing user, agent, document version, retrieval IDs, and activity ID;
- authentication and user-level row/document security;
- CI approval gates for tests, security, evaluation thresholds, and data-quality checks.

Minimum production gates:

- no critical access-control failures;
- no fabricated numeric values in financial test cases;
- citation points to the retrieved source and page;
- unanswerable questions trigger a safe fallback;
- retrieval and generation latency meet the agreed target;
- cost per request is monitored and bounded.

## 5. Proposed data model

The first implementation can add two logical tables to Supabase.

### `knowledge_documents`

Suggested fields:

- `id` — document identifier;
- `owner_id` — user or tenant owner;
- `source_uri` — file path or object-storage key;
- `file_name` — display name;
- `content_hash` — SHA-256 or equivalent content hash;
- `version` — source version number;
- `modified_at` — source modification timestamp;
- `document_type` — policy, receipt, statement, note, or other;
- `status` — discovered, processing, indexed, or failed;
- `is_active` — whether retrieval may use this version;
- `metadata` — JSON metadata that is not part of the core schema.

### `knowledge_chunks`

Suggested fields:

- `id` — chunk identifier;
- `document_id` — source document foreign key;
- `chunk_index` — position within the document;
- `page_number` — source page when available;
- `content` — extracted chunk text;
- `embedding` — vector representation;
- `token_count` — chunk size for monitoring;
- `metadata` — section, headings, tags, and retrieval hints;
- `created_at` — indexing timestamp.

The retrieval function should enforce owner and active-version filters before similarity ranking. For the current single-user prototype, this can initially be one owner, but the schema should not require a public-access model.

## 6. Security and governance decisions

- Keep transaction and budget data behind validated API or SQL tools.
- Do not expose the Supabase service key to the model or browser.
- Apply document-level ownership filters before constructing the prompt.
- Treat retrieved documents as untrusted input; protect against prompt injection in document text.
- Require explicit confirmation before any future write action.
- Log document version, retrieval identifiers, and `activity_id`, but avoid logging unnecessary receipt or financial contents.
- Version prompts, chunking settings, embedding model, and retrieval configuration.
- Add retention and deletion behavior for documents and embeddings.
- Replace the prototype’s public RLS policies before multi-user deployment.

## 7. Recommended first demonstrator

Build one end-to-end slice before adding OCR or complex orchestration:

1. Ingest Markdown and text-based PDFs containing budgeting rules and category definitions.
2. Store document metadata and page-aware chunks.
3. Generate embeddings and retrieve the top relevant chunks.
4. Expose retrieval through `retrieve_knowledge`.
5. Ask the Foundry agent questions that combine a budget tool result with a cited budgeting rule.
6. Add one changed-PDF test proving that old chunks are not returned.
7. Measure retrieval accuracy, citation accuracy, latency, and cost.

This demonstrates the complete RAG lifecycle while keeping financial calculations deterministic and avoiding unnecessary OCR complexity in the first iteration.

## 8. Interview alignment

This project can support the following interview narrative:

- **Fabric ingestion:** apply the same metadata-driven pattern to document sources and bank imports rather than creating one pipeline per source;
- **Production RAG:** map Supabase/PostgreSQL to the prototype data layer, Foundry/FastAPI to the agent-serving layer, and replace the vector component with Databricks Vector Search or Azure AI Search when required;
- **RAG components:** demonstrate extraction, chunking, embeddings, retrieval, prompt construction, citations, and response handling;
- **PDF freshness:** use hash and version detection, re-index changed documents, and cite page numbers;
- **Prompt/RAG/agent design:** keep data preparation, RAG retrieval, and approved agent tools as separate layers;
- **AI governance:** use evaluation gates, access control, deterministic business logic, audit IDs, monitoring, and human confirmation for sensitive actions.

## 9. Definition of done

The first production-shaped RAG milestone is complete when:

- documents can be ingested, versioned, chunked, embedded, and refreshed;
- retrieval is permission-filtered and returns source metadata;
- the Foundry agent can combine document evidence with structured expense tools;
- responses cite their document sources and safely decline unsupported questions;
- updated documents replace stale retrieval results;
- evaluation, logging, cost, latency, and governance checks are documented and repeatable.
