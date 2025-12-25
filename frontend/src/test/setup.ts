import "@testing-library/jest-dom";
import React from "react";
import { act, waitFor, fireEvent } from "@testing-library/react";

// Global test utilities - make these available in all test files
global.act = act;
global.waitFor = waitFor;
global.fireEvent = fireEvent;

// Type declarations for global test utilities
declare global {
  const act: typeof import("@testing-library/react").act;
  const waitFor: typeof import("@testing-library/react").waitFor;
  const fireEvent: typeof import("@testing-library/dom").fireEvent;
}

// Mock IntersectionObserver
global.IntersectionObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: jest.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock window.location
Object.defineProperty(window, "location", {
  value: {
    href: "http://localhost:3000",
    origin: "http://localhost:3000",
    protocol: "http:",
    host: "localhost:3000",
    hostname: "localhost",
    port: "3000",
    pathname: "/",
    search: "",
    hash: "",
    reload: jest.fn(),
    assign: jest.fn(),
    replace: jest.fn(),
  },
  writable: true,
});

// Mock navigator
Object.defineProperty(navigator, "clipboard", {
  value: {
    writeText: jest.fn().mockResolvedValue(undefined),
    readText: jest.fn().mockResolvedValue(""),
  },
  writable: true,
});

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn(),
};

// Mock Chart.js
jest.mock("chart.js", () => ({
  Chart: {
    register: jest.fn(),
  },
  CategoryScale: jest.fn(),
  LinearScale: jest.fn(),
  PointElement: jest.fn(),
  LineElement: jest.fn(),
  BarElement: jest.fn(),
  Title: jest.fn(),
  Tooltip: jest.fn(),
  Legend: jest.fn(),
  ArcElement: jest.fn(),
}));

jest.mock("react-chartjs-2", () => ({
  Line: jest.fn(() => React.createElement("div", { "data-testid": "line-chart" })),
  Bar: jest.fn(() => React.createElement("div", { "data-testid": "bar-chart" })),
  Pie: jest.fn(() => React.createElement("div", { "data-testid": "pie-chart" })),
  Doughnut: jest.fn(() => React.createElement("div", { "data-testid": "doughnut-chart" })),
}));

// Mock recharts
jest.mock("recharts", () => ({
  LineChart: jest.fn(() => React.createElement("div", { "data-testid": "line-chart" })),
  BarChart: jest.fn(() => React.createElement("div", { "data-testid": "bar-chart" })),
  PieChart: jest.fn(() => React.createElement("div", { "data-testid": "pie-chart" })),
  AreaChart: jest.fn(() => React.createElement("div", { "data-testid": "area-chart" })),
  Line: jest.fn(() => React.createElement("div", { "data-testid": "line" })),
  Bar: jest.fn(() => React.createElement("div", { "data-testid": "bar" })),
  Area: jest.fn(() => React.createElement("div", { "data-testid": "area" })),
  XAxis: jest.fn(() => React.createElement("div", { "data-testid": "x-axis" })),
  YAxis: jest.fn(() => React.createElement("div", { "data-testid": "y-axis" })),
  CartesianGrid: jest.fn(() => React.createElement("div", { "data-testid": "cartesian-grid" })),
  Tooltip: jest.fn(() => React.createElement("div", { "data-testid": "tooltip" })),
  Legend: jest.fn(() => React.createElement("div", { "data-testid": "legend" })),
  ResponsiveContainer: jest.fn(({ children }) =>
    React.createElement("div", { "data-testid": "responsive-container" }, children),
  ),
}));

// Mock dayjs
jest.mock("dayjs", () => {
  const mockDayjs = jest.fn(() => ({
    format: jest.fn(() => "2024-01-01"),
    toISOString: jest.fn(() => "2024-01-01T00:00:00.000Z"),
    valueOf: jest.fn(() => 1704067200000),
  }));

  (mockDayjs as typeof dayjs).extend = jest.fn();

  return mockDayjs;
});

// Global test utilities
export const createMockAsset = (overrides = {}) => ({
  id: "1",
  property_name: "测试物业",
  ownership_entity: "测试权属方",
  address: "测试地址",
  ownership_status: "已确权",
  property_nature: "经营类",
  usage_status: "出租",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  ...overrides,
});

export const createMockSearchParams = (overrides = {}) => ({
  search: "",
  page: 1,
  limit: 20,
  ...overrides,
});
