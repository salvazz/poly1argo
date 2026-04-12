import { NextRequest, NextResponse } from 'next/server'
import { getUser, deleteAnalysisSession, isSelfHostedMode, DEV_USER_ID } from '@/lib/db'
import { getAnalysisById } from '@/lib/analysis-session'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const { data: { user } } = await getUser()

    const userId = user?.id || (isSelfHostedMode() ? DEV_USER_ID : null)

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const analysis = await getAnalysisById(id, userId)

    if (!analysis) {
      return NextResponse.json({ error: 'Analysis not found' }, { status: 404 })
    }

    return NextResponse.json(analysis)
  } catch (error) {
    console.error('Failed to fetch analysis:', error)
    if (isSelfHostedMode()) {
      return NextResponse.json({ error: 'Analysis not found' }, { status: 404 })
    }
    return NextResponse.json(
      { error: 'Failed to fetch analysis' },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const { data: { user } } = await getUser()

    const userId = user?.id || (isSelfHostedMode() ? DEV_USER_ID : null)

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { error } = await deleteAnalysisSession(id, userId)

    if (error) {
      console.error('Failed to delete analysis:', error)
      return NextResponse.json(
        { error: 'Failed to delete analysis' },
        { status: 500 }
      )
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Failed to delete analysis:', error)
    if (isSelfHostedMode()) {
      return NextResponse.json({ error: 'Failed to delete analysis' }, { status: 500 })
    }
    return NextResponse.json(
      { error: 'Failed to delete analysis' },
      { status: 500 }
    )
  }
}
