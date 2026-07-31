export function quarterOf(dateString) {
  const year = Number(dateString.slice(0, 4));
  const month = Number(dateString.slice(5, 7));
  const quarter = Math.floor((month - 1) / 3) + 1;
  return { year, quarter };
}

export function quarterKey(dateString) {
  const { year, quarter } = quarterOf(dateString);
  return `${year}-Q${quarter}`;
}
