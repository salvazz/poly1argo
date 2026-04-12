import { createBrowserClient } from '@supabase/ssr'

/** No-op mock used when Supabase is not configured (self-hosted mode). */
const mockClient = {
  auth: {
    getUser: async () => ({ data: { user: null }, error: null }),
    getSession: async () => ({ data: { session: null }, error: null }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
    signOut: async () => ({ error: null }),
    verifyOtp: async () => ({ data: { user: null, session: null }, error: null }),
  },
  from: () => {
    throw new Error('Supabase not configured. This is only needed for valyu mode.')
  },
} as any

export function createClient() {
  if (process.env.NEXT_PUBLIC_APP_MODE !== 'valyu') {
    return mockClient
  }

  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}