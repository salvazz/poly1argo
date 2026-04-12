import { NextRequest, NextResponse } from 'next/server';
import { runPolymarketForecastPipeline, runUnifiedForecastPipeline } from '@/lib/agents/orchestrator';
import { getUser, isSelfHostedMode, DEV_USER_ID } from '@/lib/db';
import { createAnalysisSession, completeAnalysisSession, failAnalysisSession } from '@/lib/analysis-session';
import { parseMarketUrl, isValidMarketUrl } from '@/lib/tools/market-url-parser';
import { setValyuContext, clearValyuContext } from '@/lib/tools/valyu_search';

export const maxDuration = 800;

export async function POST(req: NextRequest) {
  let sessionId: string | null = null;

  try {
    const isSelfHosted = isSelfHostedMode();

    // Get user (optional in self-hosted mode)
    const { data: { user } } = await getUser();

    // In valyu mode, authentication is required
    if (!isSelfHosted && !user) {
      return NextResponse.json(
        { error: 'Please sign in with Valyu to analyze markets' },
        { status: 401 }
      );
    }

    console.log('[Forecast API] Mode:', isSelfHosted ? 'self-hosted' : 'valyu');
    console.log('[Forecast API] Authenticated user ID:', user?.id || 'anonymous (self-hosted mode)');
    console.log('[Forecast API] User email:', user?.email || 'none');

    const body = await req.json();
    const {
      polymarketSlug, // Legacy support
      marketUrl, // New unified support
      drivers = [],
      historyInterval = '1d',
      withBooks = true,
      withTrades = false,
      valyuAccessToken, // Valyu OAuth token for API calls - optional in dev mode
    } = body;

    // In self-hosted mode, Valyu token is optional (will use VALYU_API_KEY)
    // In valyu mode, Valyu token is required
    if (!isSelfHosted && !valyuAccessToken) {
      return NextResponse.json(
        { error: 'Valyu connection required. Please sign in with Valyu to analyze markets.' },
        { status: 401 }
      );
    }

    // Set Valyu context for tools to use (optional in self-hosted mode)
    setValyuContext(valyuAccessToken);
    console.log('[Forecast API] Valyu access token:', valyuAccessToken ? 'present (OAuth)' : 'none (will use API key in self-hosted mode)');

    // Determine which parameter was provided and validate
    let finalMarketUrl: string;
    let identifier: string;

    if (marketUrl) {
      // New unified approach - supports both Polymarket and Kalshi URLs
      if (typeof marketUrl !== 'string' || !marketUrl) {
        return NextResponse.json(
          { error: 'marketUrl must be a non-empty string' },
          { status: 400 }
        );
      }

      if (!isValidMarketUrl(marketUrl)) {
        const parsed = parseMarketUrl(marketUrl);
        return NextResponse.json(
          { error: parsed.error || 'Invalid market URL. Only Polymarket and Kalshi URLs are supported.' },
          { status: 400 }
        );
      }

      finalMarketUrl = marketUrl;
      const parsed = parseMarketUrl(marketUrl);
      identifier = parsed.identifier;
    } else if (polymarketSlug) {
      // Legacy support - convert Polymarket slug to URL
      if (typeof polymarketSlug !== 'string' || !polymarketSlug) {
        return NextResponse.json(
          { error: 'polymarketSlug must be a non-empty string' },
          { status: 400 }
        );
      }

      finalMarketUrl = `https://polymarket.com/event/${polymarketSlug}`;
      identifier = polymarketSlug;
    } else {
      return NextResponse.json(
        { error: 'Either marketUrl or polymarketSlug is required' },
        { status: 400 }
      );
    }

    // Create analysis session
    // In self-hosted mode, use DEV_USER_ID if no user is authenticated
    const userId = user?.id || (isSelfHosted ? DEV_USER_ID : null);
    if (userId) {
      const session = await createAnalysisSession(userId, finalMarketUrl);
      sessionId = session.id;
    }
    // Valyu API usage is handled via OAuth proxy in valyu mode (charged to user's org credits)
    // In self-hosted mode, uses VALYU_API_KEY directly

    // Create a ReadableStream for Server-Sent Events
    const stream = new ReadableStream({
      async start(controller) {
        const encoder = new TextEncoder();

        // Helper function to send SSE event
        const sendEvent = (data: any, event?: string) => {
          const eventData = event ? `event: ${event}\n` : '';
          const payload = `${eventData}data: ${JSON.stringify(data)}\n\n`;
          controller.enqueue(encoder.encode(payload));
        };

        // Track all analysis steps for storage
        const analysisSteps: any[] = [];

        try {
          // Send initial connection event
          sendEvent({ type: 'connected', message: 'Starting analysis...', sessionId });

          // Create progress callback for the orchestrator
          const onProgress = (step: string, details: any) => {
            // Store step for history
            analysisSteps.push({
              step,
              details,
              timestamp: new Date().toISOString()
            });

            sendEvent({
              type: 'progress',
              step,
              details,
              timestamp: new Date().toISOString()
            }, 'progress');
          };

          // Note: Valyu API usage is tracked via OAuth proxy when valyuAccessToken is set
          // API calls will be charged to the user's Valyu organization credits

          const startTime = Date.now();

          // Run unified forecasting pipeline with progress tracking (auto-detects platform)
          const forecastCard = await runUnifiedForecastPipeline({
            marketUrl: finalMarketUrl,
            drivers,
            historyInterval,
            withBooks,
            withTrades,
            onProgress,
            sessionId: sessionId || undefined,
          });

          const durationSeconds = Math.round((Date.now() - startTime) / 1000);

          // Complete the analysis session with all relevant data
          if (sessionId) {
            await completeAnalysisSession(
              sessionId,
              forecastCard.markdownReport || JSON.stringify(forecastCard),
              analysisSteps,
              forecastCard,
              {
                marketQuestion: forecastCard.question,
                p0: forecastCard.p0,
                pNeutral: forecastCard.pNeutral,
                pAware: forecastCard.pAware,
                drivers: forecastCard.drivers,
                durationSeconds,
              }
            );
          }

          // Send final result
          sendEvent({
            type: 'complete',
            forecast: forecastCard,
            sessionId,
            timestamp: new Date().toISOString()
          }, 'complete');

        } catch (error) {
          console.error('Error in forecast API:', error);

          const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

          // Mark session as failed
          if (sessionId) {
            await failAnalysisSession(sessionId, errorMessage);
          }

          sendEvent({
            type: 'error',
            error: errorMessage,
            details: error instanceof Error ? error.stack : 'No stack trace available',
            sessionId,
            timestamp: new Date().toISOString()
          }, 'error');
        } finally {
          // Clear Valyu context
          clearValyuContext();
          controller.close();
        }
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control',
      },
    });

  } catch (error) {
    console.error('Error setting up forecast stream:', error);

    // Mark session as failed if it was created
    if (sessionId) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      await failAnalysisSession(sessionId, errorMessage);
    }

    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'Unified Multi-Platform Forecasting API',
    description: 'AI-powered forecasting using GPT-5 agents - works with Polymarket and Kalshi',
    usage: 'POST with { marketUrl: string, drivers?: string[], historyInterval?: string, withBooks?: boolean, withTrades?: boolean }',
    parameters: {
      marketUrl: 'Required. Full market URL (Polymarket or Kalshi). Platform is auto-detected.',
      polymarketSlug: 'Deprecated. Use marketUrl instead. Still supported for backward compatibility.',
      drivers: 'Optional. Key factors to focus analysis on. Auto-generated if not provided.',
      historyInterval: 'Optional. Price history granularity ("1h", "4h", "1d", "1w"). Auto-optimized if not provided.',
      withBooks: 'Optional. Include order book data (default: true)',
      withTrades: 'Optional. Include recent trades (default: false)'
    },
    supportedPlatforms: {
      polymarket: {
        name: 'Polymarket',
        urlFormat: 'https://polymarket.com/event/{slug}',
        example: 'https://polymarket.com/event/will-trump-win-2024'
      },
      kalshi: {
        name: 'Kalshi',
        urlFormat: 'https://kalshi.com/markets/{series}/{category}/{ticker}',
        example: 'https://kalshi.com/markets/kxtime/times-person-of-the-year/KXTIME-25'
      }
    },
    autoGeneration: {
      drivers: 'System automatically analyzes the market question and generates relevant drivers using GPT-5',
      historyInterval: 'System selects optimal interval based on market volume, time until close, and volatility'
    },
    examples: {
      polymarket: {
        marketUrl: 'https://polymarket.com/event/will-ai-achieve-agi-by-2030'
      },
      kalshi: {
        marketUrl: 'https://kalshi.com/markets/kxgovshut/government-shutdown/kxgovshut-25oct01'
      },
      withCustomization: {
        marketUrl: 'https://polymarket.com/event/will-trump-win-2024',
        drivers: ['Polling data', 'Economic indicators', 'Swing states'],
        historyInterval: '4h'
      }
    }
  });
}
