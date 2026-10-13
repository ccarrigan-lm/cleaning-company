import { HomeProfile } from '../types';

// All profiles use the same ZIP and no pets so only home size varies.
// "medium" is the baseline home used for the six controlled scenarios.
const ZIP = '40217';

export const PROFILES: HomeProfile[] = [
  { id: 'small', label: '1 bed / 1 bath / 800 sq ft', zip: ZIP, squareFeet: 800, bedrooms: 1, bathrooms: 1, condition: 'average', pets: 'none' },
  { id: 'small-plus', label: '2 bed / 1 bath / 1,100 sq ft', zip: ZIP, squareFeet: 1100, bedrooms: 2, bathrooms: 1, condition: 'average', pets: 'none' },
  { id: 'medium', label: '3 bed / 2 bath / 1,750 sq ft (baseline)', zip: ZIP, squareFeet: 1750, bedrooms: 3, bathrooms: 2, condition: 'average', pets: 'none' },
  { id: 'large', label: '4 bed / 2.5 bath / 2,600 sq ft', zip: ZIP, squareFeet: 2600, bedrooms: 4, bathrooms: 2.5, condition: 'average', pets: 'none' },
  { id: 'xl', label: '5 bed / 3.5 bath / 3,700 sq ft', zip: ZIP, squareFeet: 3700, bedrooms: 5, bathrooms: 3.5, condition: 'average', pets: 'none' },
];

export const BASELINE_PROFILE_ID = 'medium';

export function getProfile(id: string): HomeProfile {
  const p = PROFILES.find((x) => x.id === id);
  if (!p) throw new Error(`Unknown profile "${id}". Known: ${PROFILES.map((x) => x.id).join(', ')}`);
  return p;
}
