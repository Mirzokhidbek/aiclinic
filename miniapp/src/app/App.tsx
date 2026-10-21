import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { BookingPage } from '../features/customer/BookingPage'
import { BookPage } from '../features/customer/BookPage'
import { ChatPage } from '../features/customer/ChatPage'
import { HomePage } from '../features/customer/HomePage'
import { MyBookingsPage } from '../features/customer/MyBookingsPage'
import { ServicesPage } from '../features/customer/ServicesPage'
import { AuthProvider } from './auth'
import { BackButtonBridge } from './back-button'
import { MainButtonProvider } from './main-button'
import type { TelegramEnv } from './telegram'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
})

export function App({ env }: { env: TelegramEnv }) {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider env={env}>
          <MainButtonProvider native={env.native}>
            <BackButtonBridge native={env.native} />
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/services" element={<ServicesPage />} />
              <Route path="/book/:serviceId" element={<BookPage />} />
              <Route path="/booking/:id" element={<BookingPage />} />
              <Route path="/my-bookings" element={<MyBookingsPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </MainButtonProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
