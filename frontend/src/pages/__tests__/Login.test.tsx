import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Login from "../Login";
import { AuthProvider } from "../../auth/AuthContext";
import { api } from "../../api/client";

vi.mock("../../api/client", async () => {
  const actual = await vi.importActual<typeof import("../../api/client")>("../../api/client");
  return { ...actual, api: { ...actual.api, login: vi.fn() } };
});

function renderLogin() {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <Login />
      </AuthProvider>
    </BrowserRouter>
  );
}

describe("Login page", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(api.login).mockReset();
  });

  it("submits username and password and stores tokens on success", async () => {
    vi.mocked(api.login).mockResolvedValueOnce({ access: "access-tok", refresh: "refresh-tok" });
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/username/i), "citizen");
    await user.type(screen.getByLabelText(/password/i), "S3cure-Pass!23");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith("citizen", "S3cure-Pass!23");
    });
    await waitFor(() => {
      expect(localStorage.getItem("nagrik-setu-tokens")).toContain("access-tok");
    });
  });

  it("shows an error message when login fails", async () => {
    const { ApiError } = await vi.importActual<typeof import("../../api/client")>("../../api/client");
    vi.mocked(api.login).mockRejectedValueOnce(new ApiError(401, "Invalid username or password"));
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByLabelText(/username/i), "citizen");
    await user.type(screen.getByLabelText(/password/i), "wrong");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/invalid username or password/i);
  });
});
