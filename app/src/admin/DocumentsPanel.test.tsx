import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DocumentsPanel } from "./DocumentsPanel";
import { API_BASE_URL } from "../config";

const BASE = `${API_BASE_URL}/admin/libraries/springfield-pl/documents`;

function json(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe("DocumentsPanel (Tier 8 Phase 31)", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lists documents with the staff member's token and explains the empty state", async () => {
    const fetchMock = vi.fn(async () => json([]));
    vi.stubGlobal("fetch", fetchMock);
    render(<DocumentsPanel libraryId="springfield-pl" accessToken="token-1" />);
    expect(await screen.findByText(/uses LibSync's sample policies/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(BASE, { headers: { Authorization: "Bearer token-1" } });
  });

  it("uploads a file and refreshes the list", async () => {
    const rows = [{ id: "d1", name: "fines.txt", chunk_count: 2, created_at: "2026-10-15" }];
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json([]))
      .mockResolvedValueOnce(json({ id: "d1", name: "fines.txt", chunk_count: 2 }))
      .mockResolvedValueOnce(json(rows));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<DocumentsPanel libraryId="springfield-pl" accessToken="token-1" />);
    await screen.findByText(/sample policies/i);

    await user.upload(screen.getByLabelText("Document"), new File(["Fines are $0.10."], "fines.txt"));
    await user.click(screen.getByRole("button", { name: "Upload" }));

    expect(await screen.findByText(/Added fines.txt \(2 sections\)/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Remove fines.txt" })).toBeInTheDocument();
    const [, init] = fetchMock.mock.calls[1];
    expect(init.method).toBe("POST");
    expect(init.body.get("file").name).toBe("fines.txt");
  });

  it("shows the server's explanation when a file can't be used", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(json([])).mockResolvedValueOnce(json({ detail: "Upload a PDF, text, Markdown or HTML file." }, 422)),
    );
    const user = userEvent.setup();
    render(<DocumentsPanel libraryId="springfield-pl" accessToken="token-1" />);
    await screen.findByText(/sample policies/i);
    await user.upload(screen.getByLabelText("Document"), new File(["x"], "sheet.txt"));
    await user.click(screen.getByRole("button", { name: "Upload" }));
    expect(await screen.findByText("Upload a PDF, text, Markdown or HTML file.")).toBeInTheDocument();
  });
});
