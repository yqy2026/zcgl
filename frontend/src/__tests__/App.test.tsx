import React from 'react'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import App from '../App'

// Mock the router
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

test('renders without crashing', () => {
  render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  )
})

test('renders title', () => {
  render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  )
  const titleElement = screen.getByText(/土地物业资产管理系统/i)
  expect(titleElement).toBeInTheDocument()
})