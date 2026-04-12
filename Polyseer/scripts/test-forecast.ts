#!/usr/bin/env tsx
/**
 * Test script for the Multi-Agent Forecasting System
 * 
 * This script demonstrates both Polymarket and general forecasting capabilities.
 * Run with: npm run test:forecast
 */

import 'dotenv/config';
import { runPolymarketForecastPipeline } from '../src/lib/agents/orchestrator';


// Colors for console output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

function log(color: keyof typeof colors, message: string) {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logSection(title: string) {
  console.log('\n' + '='.repeat(60));
  log('cyan', `🤖 ${title}`);
  console.log('='.repeat(60));
}

function logSubsection(title: string) {
  console.log('\n' + '-'.repeat(40));
  log('yellow', `📊 ${title}`);
  console.log('-'.repeat(40));
}

async function testPolymarketForecast() {
  logSection('POLYMARKET FORECASTING TEST');
  
  const testCases = [
    {
      name: 'AI/Technology Market',
      slug: 'will-ai-achieve-agi-by-2030',
      description: 'Testing AI-related market with auto-generated drivers'
    },
    {
      name: 'Crypto Market',
      slug: 'bitcoin-200k-by-2030',
      description: 'Testing crypto market with custom drivers',
      customDrivers: ['Institutional adoption', 'Regulatory clarity', 'Market cycles', 'Technology developments'],
      customInterval: '1d'
    },
    {
      name: 'Climate/Tech Market',
      slug: 'fusion-power-commercial-by-2035',
      description: 'Testing climate/technology market with minimal config'
    }
  ];

  for (const testCase of testCases) {
    try {
      logSubsection(`Testing: ${testCase.name}`);
      log('blue', `Description: ${testCase.description}`);
      log('blue', `Slug: ${testCase.slug}`);
      
      const startTime = Date.now();
      
      const result = await runPolymarketForecastPipeline({
        polymarketSlug: testCase.slug,
        drivers: testCase.customDrivers,
        historyInterval: testCase.customInterval,
        withBooks: true,
        withTrades: false,
      });

      const duration = ((Date.now() - startTime) / 1000).toFixed(1);
      
      log('green', '✅ SUCCESS!');
      console.log(`⏱️  Duration: ${duration}s`);
      console.log(`📈 Forecast: ${(result.pNeutral * 100).toFixed(1)}%`);
      if (result.pAware) {
        console.log(`🎯 Market-aware: ${(result.pAware * 100).toFixed(1)}%`);
      }
      console.log(`🔍 Evidence pieces: ${result.evidenceInfluence.length}`);
      console.log(`🎯 Drivers: ${result.drivers.join(', ')}`);
      console.log(`📚 Sources: ${result.provenance.length} URLs`);
      
      // Show top 3 most influential evidence
      const topEvidence = result.evidenceInfluence
        .sort((a, b) => b.deltaPP - a.deltaPP)
        .slice(0, 3);
      
      if (topEvidence.length > 0) {
        console.log('\n🏆 Top Evidence:');
        topEvidence.forEach((ev, i) => {
          console.log(`  ${i + 1}. ${ev.evidenceId} (Δ${(ev.deltaPP * 100).toFixed(1)}pp)`);
        });
      }

      // Show markdown report preview
      const reportPreview = result.markdownReport.split('\n').slice(0, 5).join('\n');
      console.log('\n📝 Report Preview:');
      console.log(reportPreview + '...');
      
    } catch (error) {
      log('red', `❌ FAILED: ${testCase.name}`);
      console.error(error);
      
      if (error instanceof Error) {
        if (error.message.includes('OPENAI_API_KEY')) {
          log('yellow', '⚠️  Make sure OPENAI_API_KEY is set in your .env file');
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          log('yellow', '⚠️  Network error - check your internet connection');
        }
      }
    }
  }
}



async function testSystemHealth() {
  logSection('SYSTEM HEALTH CHECK');
  
  const checks = [
    {
      name: 'Environment Variables',
      test: () => {
        const required = ['OPENAI_API_KEY'];
        const missing = required.filter(key => !process.env[key]);
        if (missing.length > 0) {
          throw new Error(`Missing: ${missing.join(', ')}`);
        }
        return 'All required environment variables are set';
      }
    },
   
  ];

  for (const check of checks) {
    try {
      log('blue', `Checking: ${check.name}`);
      const result = await check.test();
      log('green', `✅ ${result}`);
    } catch (error) {
      log('red', `❌ ${check.name} failed: ${error}`);
    }
  }
}

async function main() {
  log('bright', '🚀 Multi-Agent Forecasting System Test Suite');
  log('bright', '============================================');
  
  console.log('\nThis script will test the complete forecasting pipeline:');
  console.log('• System health checks');
  console.log('• Polymarket integration with auto-generation');
  console.log('• Error handling and performance metrics');
  
  try {
    // Health checks first
    await testSystemHealth();
    
    // Test Polymarket forecasting
    await testPolymarketForecast();
    
    logSection('TEST SUITE COMPLETED');
    log('green', '🎉 All tests completed! Check the results above.');
    log('yellow', '💡 Tip: Check the console logs for detailed agent interactions.');
    
  } catch (error) {
    log('red', '💥 Test suite failed with critical error:');
    console.error(error);
    process.exit(1);
  }
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  log('yellow', '\n⚠️  Test interrupted by user');
  process.exit(0);
});

process.on('unhandledRejection', (reason, promise) => {
  log('red', '💥 Unhandled promise rejection:');
  console.error(reason);
  process.exit(1);
});

// Run the test suite
if (require.main === module) {
  main().catch(error => {
    log('red', '💥 Fatal error:');
    console.error(error);
    process.exit(1);
  });
}
