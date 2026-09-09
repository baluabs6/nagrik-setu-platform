import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api, ApiError } from "../client";

const TOKENS_KEY = "nagrik-setu-tokens";

function seedTokens(access: string, refresh: string) {
  localStorage.setItem(TOKENS_KEY, JSON.stringify({ access, refresh }));
}

describe("api client", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("attaches the stored access token as a Bearer header", async () => {
    seedTokens("initial-access", "some-refresh");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ results: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await api.listIssues();

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer initial-access");
  });

  it("refreshes the access token once on a 401 and retries the request", async () => {
    seedTokens("expired-access", "valid-refresh");

    const fetchMock = vi
      .fn()
      // 1st call: original request, expired token -> 401
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) })
      // 2nd call: refresh endpoint -> new access token
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ access: "fresh-access" }) })
      // 3rd call: retried original request -> succeeds
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ results: [] }) });
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.listIssues();

    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(result).toEqual({ results: [] });
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe("Bearer fresh-access");
  });

  it("throws ApiError with the server message when the request ultimately fails", async () => {
    seedTokens("access", "refresh");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ message: "That page or resource doesn't exist." }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.stats()).rejects.toMatchObject(new ApiError(404, "That page or resource doesn't exist."));
  });
});
