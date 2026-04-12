import { NextResponse } from 'next/server';
import { getFeaturedMarkets } from '@/lib/db';

export interface FeaturedMarket {
  id: number;
  slug: string;
  question: string;
  category: string | null;
  polymarket_url: string;
  volume: number;
  end_date: string;
  current_odds: any;
  sort_order: number;
  is_active: boolean;
  updated_at?: string;
}

export interface FeaturedMarketsResponse {
  success: boolean;
  markets: FeaturedMarket[];
  count: number;
  last_updated?: string;
}

export async function GET() {
  try {
    console.log('[API] Fetching featured markets...');

    const { data: markets, error } = await getFeaturedMarkets();

    if (error) {
      console.error('[API] Database error:', error);
      return NextResponse.json(
        { success: false, error: 'Database query failed', markets: [], count: 0 },
        { status: 500 }
      );
    }

    if (!markets || markets.length === 0) {
      console.log('[API] No featured markets found');
      return NextResponse.json({
        success: true,
        markets: [],
        count: 0,
        message: 'No featured markets available'
      });
    }

    console.log(`[API] Returning ${markets.length} featured markets`);

    const response: FeaturedMarketsResponse = {
      success: true,
      markets: markets as FeaturedMarket[],
      count: markets.length,
      last_updated: markets[0]?.updated_at
    };

    // Cache for 1 hour
    return NextResponse.json(response, {
      headers: {
        'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=1800'
      }
    });

  } catch (error) {
    console.error('[API] Unexpected error:', error);

    return NextResponse.json(
      {
        success: false,
        error: 'Internal server error',
        markets: [],
        count: 0
      },
      { status: 500 }
    );
  }
}

// Optional: Handle CORS for client-side requests
export async function OPTIONS() {
  return NextResponse.json(
    {},
    {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    }
  );
}
