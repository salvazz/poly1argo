#!/usr/bin/env tsx
/**
 * Simple Demo Script for Multi-Agent Forecasting
 * 
 * Quick test with a single Polymarket forecast
 * Run with: npm run demo:simple
 */

import 'dotenv/config';
import { runPolymarketForecastPipeline } from '../src/lib/agents/orchestrator';


async function main() {
  console.log('🤖 Multi-Agent Forecasting Demo');
  console.log('================================\n');

  // Check environment
  if (!process.env.OPENAI_API_KEY) {
    console.error('❌ OPENAI_API_KEY not found in environment');
    console.log('💡 Create a .env file with: OPENAI_API_KEY=sk-...');
    process.exit(1);
  }

  console.log('✅ Environment check passed');
  console.log('🔍 Testing with a simple Polymarket forecast...\n');

  try {
    const startTime = Date.now();
    
    // Test with a popular market (auto-generates drivers and optimizes interval)
    const result = await runPolymarketForecastPipeline({
      polymarketSlug: 'lisa-cook-out-as-fed-governor-by-september-30', // Change this to test different markets
    });

    const duration = ((Date.now() - startTime) / 1000).toFixed(1);

    console.log('\n🎉 SUCCESS! Forecast completed in', duration, 'seconds');
    console.log('='.repeat(50));
    
    console.log(`📊 Question: ${result.question}`);
    console.log(`📈 Forecast Probability: ${(result.pNeutral * 100).toFixed(1)}%`);
    
    if (result.pAware) {
      console.log(`🎯 Market-Aware Probability: ${(result.pAware * 100).toFixed(1)}%`);
    }
    
    console.log(`🔍 Evidence Pieces Analyzed: ${result.evidenceInfluence.length}`);
    console.log(`🎯 Key Drivers: ${result.drivers.join(', ')}`);
    
    // Show top evidence
    const topEvidence = result.evidenceInfluence
      .sort((a, b) => b.deltaPP - a.deltaPP)
      .slice(0, 3);
    
    if (topEvidence.length > 0) {
      console.log('\n🏆 Most Influential Evidence:');
      topEvidence.forEach((ev, i) => {
        console.log(`  ${i + 1}. ${ev.evidenceId} (Impact: ${(ev.deltaPP * 100).toFixed(1)} percentage points)`);
      });
    }

    console.log('\n📝 Forecast Report:');
    console.log('-'.repeat(30));
    console.log(result.markdownReport);
    
    console.log('\n✨ Demo completed successfully!');
    console.log('💡 Try changing the polymarketSlug in demo-simple.ts to test other markets');
    
  } catch (error) {
    console.error('\n❌ Demo failed:');
    console.error(error);
    
    if (error instanceof Error) {
      if (error.message.includes('OPENAI_API_KEY')) {
        console.log('\n💡 Make sure your OpenAI API key is valid and has GPT-5 access');
      } else if (error.message.includes('network') || error.message.includes('fetch')) {
        console.log('\n💡 Check your internet connection and try again');
      } else if (error.message.includes('slug')) {
        console.log('\n💡 The Polymarket slug might be invalid. Try a different one.');
      }
    }
    
    process.exit(1);
  }
}

// Handle interruption gracefully
process.on('SIGINT', () => {
  console.log('\n⚠️  Demo interrupted by user');
  process.exit(0);
});

main().catch(error => {
  console.error('💥 Fatal error:', error);
  process.exit(1);
});
