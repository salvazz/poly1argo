import { openai } from '@ai-sdk/openai';
import { groq } from '@ai-sdk/groq';

/**
 * Centrialized model provider for Polyseer.
 * Prefers Groq if available, falls back to OpenAI.
 */
export const getModel = (size: 'small' | 'large' = 'large') => {
  const hasGroq = !!process.env.GROQ_API_KEY;
  
  if (hasGroq) {
    // Using Llama 3.3 70b as the large model and 8b as the small one
    return size === 'large' 
      ? groq('llama-3.3-70b-versatile') 
      : groq('llama-3.3-70b-versatile'); // Groq doesn't always have a good 8b small model for complex reasoning, but we can use versatile for both if needed
  }
  
  return size === 'large' ? openai('gpt-4o') : openai('gpt-4o-mini');
};
