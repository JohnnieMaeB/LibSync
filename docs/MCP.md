# LibSync for your own AI tools (MCP)

LibSync's grounded lookups are available as a [Model Context Protocol](https://modelcontextprotocol.io) server, so
library staff can use them from an AI assistant they already work in (Claude, ChatGPT, Copilot, or any MCP client).

**Endpoint:** `https://libsync.onrender.com/mcp` (Streamable HTTP, stateless; `/mcp/` works too)

| Tool | What it returns |
|---|---|
| `search_library_policies` | The library's own policy text, verbatim |
| `search_catalog` | Books from the library's catalog (or Open Library when none is connected), with availability |
| `recommend_books` | Read-alikes for a book, or books on a topic, only from titles the catalog returns |
| `search_scholarly_works` | Papers from OpenAlex, with citation counts and open-access status |
| `cite` | A citation in APA, MLA or Chicago from the work's real Crossref record |

No language model runs on LibSync's side for these calls: each tool is a direct lookup, so the answers are what the
sources say, and they cost the library nothing in AI usage.

## Your library's data

Without a key, the tools use LibSync's demo policies and Open Library. To use your library's own policies, catalog
and settings, create an API key in the staff dashboard (**Developer** panel) and send it as a header:

```
X-LibSync-Key: lsk_...
```

Your dashboard switches apply here too: a tool group you switched off, or turning the AI assistant off, turns the
matching MCP tools off.

## Connecting a client

Most clients take the endpoint URL directly (for example, a custom connector in Claude). For clients configured with
JSON, a typical entry looks like:

```json
{
  "mcpServers": {
    "libsync": {
      "type": "http",
      "url": "https://libsync.onrender.com/mcp",
      "headers": { "X-LibSync-Key": "lsk_..." }
    }
  }
}
```

Keep the key out of shared files; anyone with it can search as your library.

## Limits

30 requests a minute per address (`MCP_RATE_LIMIT_PER_MINUTE`). The operator can switch the endpoint off with
`MCP_ENABLED=0`.
