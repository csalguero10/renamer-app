export function toRoman(num) {
  const romans = [
    [1000, 'M'], [900, 'CM'], [500, 'D'], [400, 'CD'],
    [100, 'C'], [90, 'XC'], [50, 'L'], [40, 'XL'],
    [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I']
  ];
  let res = '';
  for (const [v, s] of romans) {
    while (num >= v) { res += s; num -= v; }
  }
  return res || `${num}`;
}

export function formatNumber(n, scheme="arabic", ghost=false) {
  let token = scheme === "roman" ? toRoman(n) : `${n}`;
  return ghost ? `[${token}]` : token;
}
