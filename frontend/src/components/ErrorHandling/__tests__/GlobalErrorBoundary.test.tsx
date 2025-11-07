import React from "react";
import { render, screen } from "../../../__tests__/utils/testUtils";
import { fireEvent } from "@testing-library/react";
// Jest imports - no explicit import needed for describe, it, expect

import GlobalErrorBoundary from "../GlobalErrorBoundary";

// Mock console.error to avoid noise in tests
const originalError = console.error;
beforeEach(() => {
  console.error = jest.fn();
});

afterEach(() => {
  console.error = originalError;
});

// Component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean }> = ({ shouldThrow = false }) => {
  if (shouldThrow) {
    throw new Error("Test error");
  }
  return <div>No error</div>;
};

describe("GlobalErrorBoundary", () => {
  it("renders children when there is no error", () => {
    render(
      <GlobalErrorBoundary>
        <div>Test content</div>
      </GlobalErrorBoundary>,
    );

    expect(screen.getByText("Test content")).toBeInTheDocument();
  });

  it("catches and displays error when child component throws", () => {
    render(
      <GlobalErrorBoundary>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    // Check that error UI is displayed
    expect(screen.getByText("页面出现错误")).toBeInTheDocument();
    expect(screen.getByText(/抱歉，页面遇到了一些问题/)).toBeInTheDocument();
  });

  it("displays error ID for tracking", () => {
    render(
      <GlobalErrorBoundary>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    // Check that error ID is displayed
    expect(screen.getByText("错误ID:")).toBeInTheDocument();
    expect(screen.getByText(/ERR_/)).toBeInTheDocument();
  });

  it("provides recovery actions", async () => {
    render(
      <GlobalErrorBoundary>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    // Check that recovery buttons are present - use text matching directly
    const { findByText } = screen;

    // Use text content directly as it's more reliable
    expect(await findByText("刷新页面")).toBeInTheDocument();
    expect(await findByText("返回首页")).toBeInTheDocument();
    expect(await findByText("重试")).toBeInTheDocument();
    expect(await findByText("报告问题")).toBeInTheDocument();
  });

  it("calls onError callback when error occurs", () => {
    const onError = jest.fn();

    render(
      <GlobalErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      }),
    );
  });

  it("resets error state when reset button is clicked", () => {
    const { rerender } = render(
      <GlobalErrorBoundary>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    // Error UI should be displayed
    expect(screen.getByText("页面出现错误")).toBeInTheDocument();

    // Click reset button
    const resetButton = screen.getByRole("button", { name: /重试/ });
    fireEvent.click(resetButton);

    // Rerender with no error
    rerender(
      <GlobalErrorBoundary>
        <ThrowError shouldThrow={false} />
      </GlobalErrorBoundary>,
    );

    // Should show normal content
    expect(screen.getByText("No error")).toBeInTheDocument();
  });

  it("shows detailed error information in development mode", () => {
    // Mock development environment
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "development";

    render(
      <GlobalErrorBoundary>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    // Check that development debug info is shown
    expect(screen.getByText("开发调试信息")).toBeInTheDocument();
    expect(screen.getByText("错误信息:")).toBeInTheDocument();
    expect(screen.getByText("Test error")).toBeInTheDocument();

    // Restore environment
    process.env.NODE_ENV = originalEnv;
  });

  it("hides detailed error information in production mode", () => {
    // Mock production environment
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "production";

    render(
      <GlobalErrorBoundary>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    // Check that development debug info is not shown
    expect(screen.queryByText("开发调试信息")).not.toBeInTheDocument();

    // Restore environment
    process.env.NODE_ENV = originalEnv;
  });

  it("renders custom fallback when provided", () => {
    const customFallback = <div>Custom error fallback</div>;

    render(
      <GlobalErrorBoundary fallback={customFallback}>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    expect(screen.getByText("Custom error fallback")).toBeInTheDocument();
    expect(screen.queryByText("页面出现错误")).not.toBeInTheDocument();
  });

  it("handles reload button click", () => {
    // Mock window.location.reload
    const mockReload = jest.fn();
    Object.defineProperty(window, "location", {
      value: { reload: mockReload },
      writable: true,
    });

    render(
      <GlobalErrorBoundary>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    const reloadButton = screen.getByRole("button", { name: /刷新页面/ });
    fireEvent.click(reloadButton);

    expect(mockReload).toHaveBeenCalled();
  });

  it("handles go home button click", () => {
    // Mock window.location.href
    const mockLocation = { href: "" };
    Object.defineProperty(window, "location", {
      value: mockLocation,
      writable: true,
    });

    render(
      <GlobalErrorBoundary>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    const homeButton = screen.getByRole("button", { name: /返回首页/ });
    fireEvent.click(homeButton);

    expect(mockLocation.href).toBe("/");
  });

  it("handles report bug button click", () => {
    // Mock window.open
    const mockOpen = jest.fn();
    window.open = mockOpen;

    render(
      <GlobalErrorBoundary>
        <ThrowError shouldThrow={true} />
      </GlobalErrorBoundary>,
    );

    const reportButton = screen.getByRole("button", { name: /报告问题/ });
    fireEvent.click(reportButton);

    expect(mockOpen).toHaveBeenCalledWith(expect.stringContaining("mailto:support@example.com"));
  });
});
