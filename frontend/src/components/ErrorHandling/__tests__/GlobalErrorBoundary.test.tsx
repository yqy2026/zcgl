import React from "react";
import { render, screen } from "../../../__tests__/utils/testUtils";
import { fireEvent } from "@testing-library/react";
// Jest imports - no explicit import needed for describe, it, expect

import { ErrorBoundary } from "../ErrorBoundary";

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

describe("ErrorBoundary", () => {
  it("renders children when there is no error", () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>,
    );

    expect(screen.getByText("Test content")).toBeInTheDocument();
  });

  it("catches and displays error when child component throws", () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Check that error UI is displayed
    expect(screen.getByText("页面访问出错")).toBeInTheDocument();
  });

  it("provides recovery actions", async () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Check that recovery buttons are present
    const { findByText } = screen;

    expect(await findByText(/重试/)).toBeInTheDocument();
    expect(await findByText("返回上一页")).toBeInTheDocument();
    expect(await findByText("返回首页")).toBeInTheDocument();
  });

  it("calls onError callback when error occurs", () => {
    const onError = jest.fn();

    render(
      <ErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>,
    );

    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      }),
    );
  });

  it("resets error state when retry button is clicked", () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Error UI should be displayed
    expect(screen.getByText("页面访问出错")).toBeInTheDocument();

    // Click retry button
    const retryButton = screen.getByRole("button", { name: /重试/ });
    fireEvent.click(retryButton);

    // Rerender with no error
    rerender(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>,
    );

    // Should show normal content
    expect(screen.getByText("No error")).toBeInTheDocument();
  });

  it("shows detailed error information in development mode", () => {
    // Mock development environment
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "development";

    render(
      <ErrorBoundary showErrorDetails={true}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Check that development debug info is shown
    expect(screen.getByText("错误详情 (开发模式)")).toBeInTheDocument();
    expect(screen.getByText("错误类型:")).toBeInTheDocument();
    expect(screen.getByText("Test error")).toBeInTheDocument();

    // Restore environment
    process.env.NODE_ENV = originalEnv;
  });

  it("hides detailed error information when showErrorDetails is false", () => {
    render(
      <ErrorBoundary showErrorDetails={false}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Check that development debug info is not shown
    expect(screen.queryByText("错误详情 (开发模式)")).not.toBeInTheDocument();
  });

  it("renders custom fallback when provided", () => {
    const customFallback = <div>Custom error fallback</div>;

    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Custom error fallback")).toBeInTheDocument();
    expect(screen.queryByText("页面访问出错")).not.toBeInTheDocument();
  });

  it("stores error to window object in development mode", () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "development";

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Check that error is stored in window object
    expect((window as any).__lastError).toBeDefined();
    expect((window as any).__lastError.error).toBe("Test error");

    // Restore environment
    process.env.NODE_ENV = originalEnv;
  });

  it("handles go home button click", () => {
    // Mock window.location.href
    const mockLocation = { href: "" };
    Object.defineProperty(window, "location", {
      value: mockLocation,
      writable: true,
    });

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>,
    );

    const homeButton = screen.getByRole("button", { name: /返回首页/ });
    fireEvent.click(homeButton);

    expect(mockLocation.href).toBe("/dashboard");
  });

  it("shows retry counter", () => {
    render(
      <ErrorBoundary maxRetries={2}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Should show retry counter (0/2)
    expect(screen.getByText(/重试 \(0\/2\)/)).toBeInTheDocument();
  });
});
