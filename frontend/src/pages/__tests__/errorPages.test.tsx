import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import NotFound from "../errors/NotFound";
import Forbidden from "../errors/Forbidden";
import ServerError from "../errors/ServerError";
import ServiceUnavailable from "../errors/ServiceUnavailable";
import BadRequest from "../errors/BadRequest";

function renderWithRouter(ui: React.ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>);
}

describe("error pages", () => {
  it("renders 404 with the right code and a link home", () => {
    renderWithRouter(<NotFound />);
    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByText(/gone missing/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to home/i })).toHaveAttribute("href", "/");
  });

  it("renders 403 forbidden messaging", () => {
    renderWithRouter(<Forbidden />);
    expect(screen.getByText("403")).toBeInTheDocument();
    expect(screen.getByText(/don't have access/i)).toBeInTheDocument();
  });

  it("renders 400 bad request messaging", () => {
    renderWithRouter(<BadRequest />);
    expect(screen.getByText("400")).toBeInTheDocument();
  });

  it("renders 500 with the signal accent class", () => {
    renderWithRouter(<ServerError />);
    const code = screen.getByText("500");
    expect(code.className).toContain("error-page__code--signal");
  });

  it("renders 503 with the turmeric accent class", () => {
    renderWithRouter(<ServiceUnavailable />);
    const code = screen.getByText("503");
    expect(code.className).toContain("error-page__code--turmeric");
  });
});
