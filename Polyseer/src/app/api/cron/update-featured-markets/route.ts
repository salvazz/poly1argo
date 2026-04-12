import { NextRequest, NextResponse } from 'next/server';
import { createServiceClient } from '@/utils/supabase/server';
import { isSelfHostedMode } from '@/lib/local-db/local-auth';

interface PolymarketMarket {
  id: string;
  question: string;
  slug: string;
  category: string;
  volume: number;
  endDate: string;
  active: boolean;
  outcomes?: any[];
}

interface FeaturedMarket {
  slug: string;
  question: string;
  category: string | null;
  polymarket_url: string;
  volume: number;
  end_date: string;
  current_odds: any;
  sort_order: number;
}

export async function GET(request: NextRequest) {
  try {
    // Self-hosted mode uses local SQLite — cron updates are not applicable
    if (isSelfHostedMode()) {
      return NextResponse.json({ success: true, skipped: true, reason: 'self-hosted mode' });
    }

    // Verify request is from Vercel cron
    const userAgent = request.headers.get('user-agent');
    if (userAgent !== 'vercel-cron/1.0') {
      console.log('[Cron] Unauthorized request from:', userAgent);
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    console.log('[Cron] Starting featured markets update...');

    // Fetch trending markets from Polymarket with bias
    const trendingMarkets = await fetchTrendingWithBias();
    
    if (!trendingMarkets || trendingMarkets.length === 0) {
      console.log('[Cron] No trending markets found');
      return NextResponse.json({ error: 'No markets found' }, { status: 500 });
    }

    // Update Supabase table using service role
    const supabase = createServiceClient();
    
    // Clear existing markets
    const { error: deleteError } = await supabase
      .from('featured_markets')
      .delete()
      .neq('id', 0); // Delete all rows
    
    if (deleteError) {
      console.error('[Cron] Error clearing markets:', deleteError);
      return NextResponse.json({ error: 'Database clear failed' }, { status: 500 });
    }

    // Insert new trending markets
    const { error: insertError } = await supabase
      .from('featured_markets')
      .insert(trendingMarkets);
    
    if (insertError) {
      console.error('[Cron] Error inserting markets:', insertError);
      return NextResponse.json({ error: 'Database insert failed' }, { status: 500 });
    }

    console.log(`[Cron] Successfully updated ${trendingMarkets.length} trending markets`);
    
    return NextResponse.json({ 
      success: true, 
      updated: trendingMarkets.length,
      markets: trendingMarkets.map(m => ({ slug: m.slug, question: m.question }))
    });

  } catch (error) {
    console.error('[Cron] Update failed:', error);
    return NextResponse.json({ 
      error: 'Cron job failed', 
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

async function fetchTrendingWithBias(): Promise<FeaturedMarket[]> {
  try {
    const utcHour = new Date().getUTCHours();
    
    // Category bias weights based on UTC time
    const categoryBias = {
      'Crypto': utcHour >= 0 && utcHour < 8 ? 1.5 : 1.0,
      'US-current-affairs': utcHour >= 8 && utcHour < 16 ? 1.5 : 1.0,
      'Sports': utcHour >= 16 && utcHour < 20 ? 1.3 : 1.0,
      'Pop-Culture': utcHour >= 20 && utcHour < 24 || utcHour < 4 ? 1.2 : 1.0
    };

    console.log(`[Cron] Fetching markets with bias for hour ${utcHour}:`, categoryBias);

    // Fetch from Polymarket Gamma API
    const response = await fetch(
      'https://gamma-api.polymarket.com/markets?' + 
      new URLSearchParams({
        active: 'true',
        volume_num_min: '50000',
        limit: '50',
        closed: 'false'
      })
    );

    if (!response.ok) {
      throw new Error(`Polymarket API error: ${response.status}`);
    }

    const markets: PolymarketMarket[] = await response.json();
    console.log(`[Cron] Fetched ${markets.length} markets from Polymarket`);

    // Apply bias scoring
    const scoredMarkets = markets
      .filter(market => 
        market.active && 
        market.volume >= 50000 &&
        market.endDate &&
        new Date(market.endDate) > new Date(Date.now() + 3 * 24 * 60 * 60 * 1000) // At least 3 days left
      )
      .map(market => ({
        ...market,
        biased_score: market.volume * (categoryBias[market.category as keyof typeof categoryBias] || 1.0)
      }))
      .sort((a, b) => b.biased_score - a.biased_score);

    // Select diverse top markets (max 3 per category)
    const selected = selectTopDiverse(scoredMarkets, 10);
    console.log(`[Cron] Selected ${selected.length} diverse markets`);

    // Transform to database format WITH LIVE ODDS
    const featuredMarkets: FeaturedMarket[] = [];
    
    for (let index = 0; index < selected.length; index++) {
      const market = selected[index];
      
      // Fetch live odds using the same approach as analysis
      let currentOdds = null;
      try {
        const liveOdds = await fetchMarketOdds(market.slug);
        currentOdds = liveOdds;
        console.log(`[Cron] Got live odds for ${market.slug}:`, liveOdds);
      } catch (error) {
        console.log(`[Cron] Could not fetch odds for ${market.slug}:`, error instanceof Error ? error.message : String(error));
      }
      
      featuredMarkets.push({
        slug: market.slug,
        question: market.question,
        category: null, // No category from Polymarket API
        polymarket_url: `https://polymarket.com/event/${market.slug}`,
        volume: Math.floor(market.volume), // Convert to integer
        end_date: market.endDate,
        current_odds: currentOdds,
        sort_order: index
      });
    }

    return featuredMarkets;

  } catch (error) {
    console.error('[Cron] Error fetching trending markets:', error);
    throw error;
  }
}

// Helper function to fetch live market odds (same approach as analysis)
async function fetchMarketOdds(slug: string): Promise<any> {
  try {
    // Step 1: Get market details from Gamma API to get token_map
    const marketResponse = await fetch(
      `https://gamma-api.polymarket.com/markets?slug=${encodeURIComponent(slug)}`
    );
    
    if (!marketResponse.ok) {
      throw new Error(`Failed to fetch market details: ${marketResponse.status}`);
    }
    
    const markets = await marketResponse.json();
    if (!Array.isArray(markets) || markets.length === 0) {
      throw new Error('No market found for slug');
    }
    
    const market = markets[0];
    
    // Step 2: Extract token IDs and outcomes from the market data
    let tokenIds: string[] = [];
    let outcomes: string[] = [];
    
    try {
      // Parse outcomes and token IDs from JSON strings
      if (market.outcomes && typeof market.outcomes === 'string') {
        outcomes = JSON.parse(market.outcomes);
      }
      
      if (market.clobTokenIds && typeof market.clobTokenIds === 'string') {
        tokenIds = JSON.parse(market.clobTokenIds);
      }
      
      // If we have current prices, we can return them directly
      if (market.outcomePrices && typeof market.outcomePrices === 'string') {
        const prices = JSON.parse(market.outcomePrices);
        if (prices.length === outcomes.length) {
          const oddsMap: Record<string, number> = {};
          outcomes.forEach((outcome, index) => {
            oddsMap[outcome.toLowerCase()] = parseFloat(prices[index]);
          });
          
          // Return in standard format
          if (oddsMap.yes !== undefined && oddsMap.no !== undefined) {
            console.log(`[Cron] Using direct prices for ${slug}:`, { yes: oddsMap.yes, no: oddsMap.no });
            return { yes: oddsMap.yes, no: oddsMap.no };
          } else {
            console.log(`[Cron] Using direct prices for ${slug}:`, oddsMap);
            return oddsMap;
          }
        }
      }
    } catch (parseError) {
      console.log(`[Cron] Error parsing market data for ${slug}:`, parseError instanceof Error ? parseError.message : String(parseError));
    }
    
    // Fallback: if parsing failed or no direct prices, continue with CLOB API
    if (tokenIds.length === 0 || outcomes.length === 0) {
      console.log(`[Cron] No valid tokens/outcomes found for market ${slug}`);
      return null;
    }
    
    // Step 3: Fetch current prices from CLOB API as fallback
    const odds: Record<string, number> = {};
    
    for (let i = 0; i < outcomes.length && i < tokenIds.length; i++) {
      const outcome = outcomes[i];
      const tokenId = tokenIds[i];
      
      try {
        // Fetch both buy and sell prices
        const [buyResponse, sellResponse] = await Promise.all([
          fetch(`https://clob.polymarket.com/price?token_id=${encodeURIComponent(tokenId)}&side=buy`),
          fetch(`https://clob.polymarket.com/price?token_id=${encodeURIComponent(tokenId)}&side=sell`)
        ]);
        
        let price = 0.5; // Default fallback
        
        if (buyResponse.ok && sellResponse.ok) {
          const buyData = await buyResponse.json();
          const sellData = await sellResponse.json();
          
          const buyPrice = buyData?.price ? parseFloat(buyData.price) : null;
          const sellPrice = sellData?.price ? parseFloat(sellData.price) : null;
          
          // Use mid price if both available, otherwise use what we have
          if (buyPrice !== null && sellPrice !== null) {
            price = (buyPrice + sellPrice) / 2;
          } else if (buyPrice !== null) {
            price = buyPrice;
          } else if (sellPrice !== null) {
            price = sellPrice;
          }
        }
        
        odds[outcome.toLowerCase()] = price;
        
      } catch (tokenError) {
        console.log(`[Cron] Error fetching price for token ${tokenId}:`, tokenError instanceof Error ? tokenError.message : String(tokenError));
        odds[outcome.toLowerCase()] = 0.5; // Fallback
      }
    }
    
    // Return in a standard format (yes/no for binary markets)
    if (odds.yes !== undefined && odds.no !== undefined) {
      return { yes: odds.yes, no: odds.no };
    } else {
      // For non-binary markets, return all outcomes
      return odds;
    }
    
  } catch (error) {
    console.log(`[Cron] Error fetching odds for ${slug}:`, error instanceof Error ? error.message : String(error));
    throw error;
  }
}

function selectTopDiverse(markets: any[], maxCount: number): any[] {
  const selected: any[] = [];
  const categoryCount: Record<string, number> = {};
  const maxPerCategory = 3;

  // Sort by biased score
  const sorted = markets.sort((a, b) => b.biased_score - a.biased_score);

  for (const market of sorted) {
    if (selected.length >= maxCount) break;
    
    const category = market.category || 'Other';
    const currentCount = categoryCount[category] || 0;
    
    // Add if we haven't hit the per-category limit
    if (currentCount < maxPerCategory) {
      selected.push(market);
      categoryCount[category] = currentCount + 1;
    }
  }

  // If we still have slots and strict diversity prevented good markets, fill remaining
  if (selected.length < maxCount) {
    for (const market of sorted) {
      if (selected.length >= maxCount) break;
      if (!selected.find(s => s.id === market.id)) {
        selected.push(market);
      }
    }
  }

  return selected;
}

function extractOdds(outcomes: any[]): any {
  if (!outcomes || outcomes.length === 0) return null;
  
  try {
    // Handle binary outcomes (Yes/No)
    if (outcomes.length === 2) {
      const yes = outcomes.find(o => o.outcome?.toLowerCase().includes('yes'));
      const no = outcomes.find(o => o.outcome?.toLowerCase().includes('no'));
      
      if (yes && no) {
        return {
          yes: yes.price || yes.probability || 0.5,
          no: no.price || no.probability || 0.5
        };
      }
    }
    
    // Handle multiple outcomes
    const odds: Record<string, number> = {};
    outcomes.forEach((outcome, index) => {
      const key = outcome.outcome || `option_${index + 1}`;
      odds[key] = outcome.price || outcome.probability || 0;
    });
    
    return odds;
  } catch (error) {
    console.error('[Cron] Error extracting odds:', error);
    return null;
  }
}