#!/usr/bin/env tsx
/**
 * Debug script to test driver generation
 */

import 'dotenv/config';
import { generateDrivers, generateFallbackDrivers } from '../src/lib/agents/driver-generator';

async function testDriverGeneration() {
  console.log('🔍 Testing driver generation...');
  
  // Mock market data
  const mockMarketData = {
    market_facts: {
      question: 'Will the Federal Reserve cut interest rates in September 2025?',
      volume: 1000000,
      liquidity: 500000,
    },
    market_state_now: [{
      outcome: 'Yes',
      mid: 0.65
    }]
  };

  try {
    console.log('📊 Market question:', mockMarketData.market_facts.question);
    
    const drivers = await generateDrivers(mockMarketData);
    
    console.log('✅ Generated drivers:', drivers);
    console.log('📈 Number of drivers:', drivers.length);
    
    if (drivers.length > 5) {
      console.log('⚠️  WARNING: Too many drivers generated!');
    } else {
      console.log('✅ Driver count looks good');
    }
    
  } catch (error) {
    console.error('❌ Error generating drivers:', error);
    
    // Test fallback
    console.log('🔄 Testing fallback drivers...');
    const fallbackDrivers = generateFallbackDrivers(mockMarketData.market_facts.question);
    console.log('🔄 Fallback drivers:', fallbackDrivers);
    console.log('📈 Fallback count:', fallbackDrivers.length);
  }
}

testDriverGeneration().catch(console.error);
