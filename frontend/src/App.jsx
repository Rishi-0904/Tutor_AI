import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuth } from './hooks/useAuth'
import LoginPage from './components/auth/LoginPage'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Navbar from './components/shared/Navbar'
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'
import ChatPage from './pages/ChatPage'
import QuizPage from './pages/QuizPage'
import OCRPage from './pages/OCRPage'
import ProfilePage from './pages/ProfilePage'
import AnalyticsPage from './pages/AnalyticsPage'

function AppLayout({ children }) {
  return (
    <div className="h-screen flex flex-row bg-[#080b14] overflow-hidden">
      <Navbar />
      <main className="flex-1 flex overflow-hidden min-w-0">
        {children}
      </main>
    </div>
  )
}

export default function App() {
  useAuth() // Initializes auth listener

  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <AppLayout><Dashboard /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <AppLayout><ChatPage /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/quiz"
            element={
              <ProtectedRoute>
                <AppLayout><QuizPage /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/vision"
            element={
              <ProtectedRoute>
                <AppLayout><OCRPage /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <AppLayout><ProfilePage /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute>
                <AppLayout><AnalyticsPage /></AppLayout>
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>

      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e2436',
            color: '#e2e8f0',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: '12px',
            fontSize: '14px',
          },
          success: { iconTheme: { primary: '#4f6ef7', secondary: '#fff' } },
        }}
      />
    </>
  )
}
