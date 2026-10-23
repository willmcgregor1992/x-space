import { render, screen } from "@testing-library/react";
import { ApiErrorBanner } from "./DashboardPage";

describe("API failure state", () => {
  it("renders a polished error without a stack trace", () => {
    render(<ApiErrorBanner show />);
    expect(screen.getByText(/Source unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText(/traceback/i)).not.toBeInTheDocument();
  });
});
