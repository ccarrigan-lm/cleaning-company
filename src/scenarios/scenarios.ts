import { Scenario } from '../types';

// Six controlled scenarios: each changes exactly one factor from the baseline.
export const SCENARIOS: Scenario[] = [
  { id: 'baseline', label: 'One-time standard cleaning, no extras', cleaningType: 'standard', frequency: 'one_time', extras: [] },
  { id: 'recurring', label: 'Biweekly standard cleaning', cleaningType: 'standard', frequency: 'biweekly', extras: [] },
  { id: 'deep', label: 'One-time deep cleaning', cleaningType: 'deep', frequency: 'one_time', extras: [] },
  { id: 'oven', label: 'Standard cleaning plus oven interior', cleaningType: 'standard', frequency: 'one_time', extras: ['oven_interior'] },
  { id: 'fridge', label: 'Standard cleaning plus refrigerator interior', cleaningType: 'standard', frequency: 'one_time', extras: ['fridge_interior'] },
  { id: 'partial', label: 'Kitchen and bathrooms only', cleaningType: 'standard', frequency: 'one_time', extras: [], areasOnly: ['kitchen', 'bathrooms'] },
];

export function getScenario(id: string): Scenario {
  const s = SCENARIOS.find((x) => x.id === id);
  if (!s) throw new Error(`Unknown scenario "${id}". Known: ${SCENARIOS.map((x) => x.id).join(', ')}`);
  return s;
}
