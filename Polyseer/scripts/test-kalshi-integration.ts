/**
 * Test script for Kalshi integration
 * Run with: npm run tsx scripts/test-kalshi-integration.ts
 */

import { parseMarketUrl, isValidMarketUrl } from '../src/lib/tools/market-url-parser';
import { buildLLMPayloadFromKalshiTicker } from '../src/lib/tools/kalshi';

async function testUrlParsing() {
  console.log('\n🧪 Testing URL Parsing...\n');

  const testUrls = [
    'https://polymarket.com/event/will-trump-win-2024',
    'https://kalshi.com/markets/kxtime/times-person-of-the-year/KXTIME-25',
    'https://kalshi.com/markets/kxgovshut/government-shutdown/kxgovshut-25oct01',
    'https://example.com/invalid',
  ];

  for (const url of testUrls) {
    const parsed = parseMarketUrl(url);
    console.log(`URL: ${url}`);
    console.log(`  Valid: ${parsed.valid}`);
    console.log(`  Platform: ${parsed.platform}`);
    console.log(`  Identifier: ${parsed.identifier}`);
    if (parsed.error) console.log(`  Error: ${parsed.error}`);
    console.log();
  }
}

async function testKalshiAPI() {
  console.log('\n🧪 Testing Kalshi API Integration...\n');

  // Test with a real Kalshi ticker
  const testTicker = 'KXTIME-25'; // TIME's Person of the Year 2025

  try {
    console.log(`Fetching data for ticker: ${testTicker}...`);
    const payload = await buildLLMPayloadFromKalshiTicker(testTicker, {
      withBooks: false,
      withTrades: false
    });

    console.log('\n✅ Successfully fetched Kalshi market data:');
    console.log(`  Question: ${payload.market_facts.question}`);
    console.log(`  Volume: $${payload.market_facts.volume?.toLocaleString() || 'N/A'}`);
    console.log(`  Liquidity: $${payload.market_facts.liquidity?.toLocaleString() || 'N/A'}`);
    console.log(`  Close Time: ${payload.market_facts.close_time}`);
    console.log(`  Resolution Source: ${payload.market_facts.resolution_source}`);
    console.log(`\n  Outcomes:`);

    for (const outcome of payload.market_state_now) {
      console.log(`    ${outcome.outcome}: Bid=${outcome.bid}, Ask=${outcome.ask}, Mid=${outcome.mid}`);
    }

    console.log(`\n  Price History Points: ${payload.history[0]?.points.length || 0}`);

    if (payload.event_summary?.is_multi_candidate) {
      console.log(`\n  Multi-Candidate Event:`);
      console.log(`    Total Markets: ${payload.event_summary.total_markets}`);
      console.log(`    Active Markets: ${payload.event_summary.active_markets}`);
      console.log(`    Top Candidates:`);
      payload.event_summary.top_candidates.slice(0, 5).forEach((c, i) => {
        console.log(`      ${i + 1}. ${c.name}: ${(c.implied_probability * 100).toFixed(1)}%`);
      });
    }

  } catch (error) {
    console.error('\n❌ Error fetching Kalshi data:', error);
    if (error instanceof Error) {
      console.error(`   Message: ${error.message}`);
    }
  }
}

async function main() {
  console.log('='.repeat(60));
  console.log('🚀 Kalshi Integration Test Suite');
  console.log('='.repeat(60));

  await testUrlParsing();
  await testKalshiAPI();

  console.log('\n' + '='.repeat(60));
  console.log('✅ Test suite completed!');
  console.log('='.repeat(60) + '\n');
}

main().catch(console.error);