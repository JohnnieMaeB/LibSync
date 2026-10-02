"""Live behavioral evals for the LibSync agent (pydantic-evals).

Unlike `tests/`, which mocks every model and external API, these run the
real agent against the real Groq/Pinecone/Open Library/OpenAlex/Crossref
stack and check *behavior*: did it call the right tool, ground its answer in
the seed data, and stay honest when it doesn't know. See evals/README.md.
"""
