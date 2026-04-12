'use server'

import { getUserById, isSelfHostedMode, DEV_USER_ID } from '@/lib/db'

export async function getUserData(userId: string) {
  try {
    // In self-hosted mode, if requesting dev user, return mock data
    if (isSelfHostedMode() && userId === DEV_USER_ID) {
      return {
        id: DEV_USER_ID,
        email: 'dev@localhost',
        full_name: 'Development User',
        subscription_tier: 'unlimited',
        subscription_status: 'active',
      }
    }

    const { data, error } = await getUserById(userId)

    if (error) {
      console.error('[Server Action] Error fetching user data:', error)
      return null
    }

    return data
  } catch (error) {
    console.error('[Server Action] Exception fetching user data:', error)
    return null
  }
}
