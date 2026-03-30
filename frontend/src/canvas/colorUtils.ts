export function hex(r: number, g: number, b: number) {
  return (r << 16) | (g << 8) | b;
}

export function darken(color: number, t: number) {
  const r = Math.round(((color >> 16) & 0xff) * (1 - t));
  const g = Math.round(((color >> 8) & 0xff) * (1 - t));
  const b = Math.round((color & 0xff) * (1 - t));
  return (r << 16) | (g << 8) | b;
}

export function lighten(color: number, t: number) {
  const r = Math.round(((color >> 16) & 0xff) + (255 - ((color >> 16) & 0xff)) * t);
  const g = Math.round(((color >> 8) & 0xff) + (255 - ((color >> 8) & 0xff)) * t);
  const b = Math.round((color & 0xff) + (255 - (color & 0xff)) * t);
  return (r << 16) | (g << 8) | b;
}
