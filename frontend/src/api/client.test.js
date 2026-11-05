import { describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch, errorMessage } from "./client.js";
import { shouldRetry } from "./queryClient.js";

function respond(status, body) {
  globalThis.fetch = vi.fn(async () => new Response(body === undefined ? null : JSON.stringify(body), { status }));
  return globalThis.fetch;
}

describe("apiFetch", () => {
  it("prefixes /api and returns parsed JSON", async () => {
    const fetchMock = respond(200, { status: "ok" });

    await expect(apiFetch("/health")).resolves.toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledWith("/api/health", expect.objectContaining({ method: "GET" }));
  });

  it("sends a JSON body with a content type", async () => {
    const fetchMock = respond(201, { id: 1 });

    await apiFetch("/bills", { method: "POST", body: { name: "Rent" } });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers).toEqual({ "Content-Type": "application/json" });
    expect(options.body).toBe('{"name":"Rent"}');
  });

  it("returns null for 204 No Content", async () => {
    respond(204);

    await expect(apiFetch("/bills/1", { method: "DELETE" })).resolves.toBeNull();
  });

  it("throws ApiError with the server's message", async () => {
    respond(404, { detail: "Bill 9 not found" });

    await expect(apiFetch("/bills/9")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "Bill 9 not found",
    });
  });

  it("throws ApiError even when the error body is not JSON", async () => {
    globalThis.fetch = vi.fn(async () => new Response("Bad Gateway", { status: 502 }));

    await expect(apiFetch("/health")).rejects.toMatchObject({ status: 502, message: "Request failed (502)" });
  });
});

describe("errorMessage", () => {
  it("joins FastAPI validation errors with their field names", () => {
    const body = {
      detail: [
        { loc: ["body", "amount"], msg: "Input should be greater than 0" },
        { loc: ["body", "name"], msg: "String should have at least 1 character" },
      ],
    };

    expect(errorMessage(body, 422)).toBe(
      "amount: Input should be greater than 0; name: String should have at least 1 character"
    );
  });
});

describe("shouldRetry", () => {
  it("never retries requests the server rejected", () => {
    expect(shouldRetry(0, new ApiError(422, "bad"))).toBe(false);
  });

  it("retries server and network errors up to twice", () => {
    expect(shouldRetry(0, new ApiError(503, "down"))).toBe(true);
    expect(shouldRetry(1, new TypeError("Failed to fetch"))).toBe(true);
    expect(shouldRetry(2, new TypeError("Failed to fetch"))).toBe(false);
  });
});
