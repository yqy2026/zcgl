import React from 'react'
import BusinessLayout from './components/Layout/BusinessLayout'
import AppRoutes from './routes/AppRoutes'
import './App.css'

const App: React.FC = () => {
  return (
    <BusinessLayout>
      <AppRoutes />
    </BusinessLayout>
  )
}

export default App