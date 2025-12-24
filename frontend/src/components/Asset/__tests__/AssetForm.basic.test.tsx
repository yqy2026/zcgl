import React from "react";
// Jest imports - no explicit import needed for describe, it, expect
import { render, screen } from "../../../__tests__/utils/testUtils";

import { AssetForm } from "../../Forms";

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn(),
};
global.localStorage = localStorageMock;

// Mock the hooks and dependencies
jest.mock("@/hooks/useFormFieldVisibility", () => ({
  useFormFieldVisibility: () => ({
    isFieldVisible: jest.fn(() => true),
    isFieldHidden: jest.fn(() => false),
    getFieldDependencies: jest.fn(() => []),
    getAllVisibleFields: jest.fn(() => []),
    getAllHiddenFields: jest.fn(() => []),
    visibleFields: new Set(),
    hiddenFields: new Set(),
  }),
  useFormGroupVisibility: () => ({
    isGroupVisible: jest.fn(() => true),
    getVisibleFieldsInGroup: jest.fn(() => ["property_name", "ownership_entity"]),
    getHiddenFieldsInGroup: jest.fn(() => []),
  }),
}));

jest.mock("@/utils/format", () => ({
  calculateOccupancyRate: jest.fn(() => 80),
}));

// Mock the dictionary hooks to avoid API calls
jest.mock("@/hooks/useDictionary", () => ({
  useDictionaries: jest.fn(() => ({})),
  useDictionary: jest.fn(() => ({
    options: [],
    loading: false,
    error: null,
  })),
}));

// Mock DictionarySelect component
jest.mock("@/components/Dictionary/DictionarySelect", () => {
  return {
    __esModule: true,
    default: ({ placeholder }: any) => (
      <div data-testid="dictionary-select">{placeholder || "Select"}</div>
    ),
    DictionarySelect: ({ placeholder }: any) => (
      <div data-testid="dictionary-select">{placeholder || "Select"}</div>
    ),
  };
});

// Mock OwnershipSelect and ProjectSelect components
jest.mock("@/components/Ownership/OwnershipSelect", () => {
  return {
    __esModule: true,
    default: ({ placeholder }: any) => (
      <div data-testid="ownership-select">{placeholder || "Select Ownership"}</div>
    ),
  };
});

jest.mock("@/components/Project/ProjectSelect", () => {
  return {
    __esModule: true,
    default: ({ placeholder }: any) => (
      <div data-testid="project-select">{placeholder || "Select Project"}</div>
    ),
  };
});

// Mock GroupedSelectSingle component
jest.mock("@/components/Common/GroupedSelect", () => {
  return {
    __esModule: true,
    default: ({ placeholder }: any) => (
      <div data-testid="grouped-select">{placeholder || "Select Option"}</div>
    ),
  };
});

describe("AssetForm Basic Tests", () => {
  const mockProps = {
    onSubmit: jest.fn(),
    onCancel: jest.fn(),
    loading: false,
    mode: "create" as const,
  };

  it("renders without crashing", () => {
    render(<AssetForm {...mockProps} />);

    // Check if the form is rendered
    expect(screen.getByText("表单完成度")).toBeInTheDocument();
  });

  it("shows form completion progress", () => {
    render(<AssetForm {...mockProps} />);

    // Check if progress bar is present
    expect(screen.getByText("表单完成度")).toBeInTheDocument();
  });

  it("renders basic form sections", () => {
    render(<AssetForm {...mockProps} />);

    // Check if basic sections are rendered
    expect(screen.getByText("基本信息")).toBeInTheDocument();
    expect(screen.getByText("面积信息")).toBeInTheDocument();
    expect(screen.getByText("状态信息")).toBeInTheDocument();
  });

  it("shows action buttons", async () => {
    render(<AssetForm {...mockProps} />);

    // Wait for buttons to be present since they might render asynchronously
    const { findByText } = screen;
    expect(await findByText("取消")).toBeInTheDocument();
    expect(await findByText("重置")).toBeInTheDocument();
    expect(await findByText("创建资产")).toBeInTheDocument();
  });

  it("shows edit mode button text", () => {
    render(<AssetForm {...mockProps} mode="edit" />);

    // Check if edit mode button text is correct
    expect(screen.getByRole("button", { name: /更新资产/i })).toBeInTheDocument();
  });

  it("shows advanced options toggle", () => {
    render(<AssetForm {...mockProps} />);

    // Check if advanced options section is present
    expect(screen.getByText("高级选项")).toBeInTheDocument();
  });
});
