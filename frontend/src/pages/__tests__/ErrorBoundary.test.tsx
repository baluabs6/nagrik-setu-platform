import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import ErrorBoundary from "../errors/ErrorBoundary";

function Bomb(): JSX.Element {
  throw new Error("boom");
}

describe("ErrorBoundary", () => {
  it("renders children when there is no error", () => {
    render(
      <ErrorBoundary>
        <p>All good</p>
      </ErrorBoundary>
    );
    expect(screen.getByText("All good")).toBeInTheDocument();
  });

  it("renders the 500 page when a child throws during render", () => {
    // React logs the caught error to console.error; silence it so the
    // test output stays clean while still asserting it happened.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <BrowserRouter>
        <ErrorBoundary>
          <Bomb />
        </ErrorBoundary>
      </BrowserRouter>
    );
    expect(screen.getByText("500")).toBeInTheDocument();
    expect(screen.getByText(/something went wrong on our end/i)).toBeInTheDocument();
    spy.mockRestore();
  });
});
