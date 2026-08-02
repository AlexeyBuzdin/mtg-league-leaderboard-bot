const _SEASONS = ['winter', 'spring', 'summer', 'autumn'];
const _LABELS = { winter: 'Winter', spring: 'Spring', summer: 'Summer', autumn: 'Autumn' };
const _MONTH_INDEX = {
  1: 0, 2: 0, 12: 0,
  3: 1, 4: 1, 5: 1,
  6: 2, 7: 2, 8: 2,
  9: 3, 10: 3, 11: 3,
};

export function seasonOf(dateString) {
  const year = Number(dateString.slice(0, 4));
  const month = Number(dateString.slice(5, 7));
  const index = _MONTH_INDEX[month];
  const seasonYear = month === 12 ? year + 1 : year;
  return { year: seasonYear, season: _SEASONS[index], index };
}

export function seasonKey(dateString) {
  const { year, index } = seasonOf(dateString);
  return `${year}-${index}`;
}

export function seasonLabel(dateString) {
  const { year, season } = seasonOf(dateString);
  return `${_LABELS[season]} ${year}`;
}
