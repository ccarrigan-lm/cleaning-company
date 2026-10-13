import { Adapter } from './types';
import { scrubLouAdapter } from './scrubLou';

export const ADAPTERS: Record<string, Adapter> = {
  [scrubLouAdapter.id]: scrubLouAdapter,
  // 'maids-in-apron': ...           (step 7)
  // 'super-cleaning-louisville': ... (step 7)
};

export function getAdapter(id: string): Adapter {
  const a = ADAPTERS[id];
  if (!a) throw new Error(`No adapter for "${id}". Available: ${Object.keys(ADAPTERS).join(', ')}`);
  return a;
}
