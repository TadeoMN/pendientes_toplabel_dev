function colorTextoSobre(hex) {
  const oscuro = '#0f172a';
  if (typeof hex !== 'string' || !/^#(?:[\da-f]{3}|[\da-f]{6})$/i.test(hex)) return oscuro;
  let color = hex.slice(1);
  if (color.length === 3) color = Array.from(color, c => c + c).join('');
  function luminancia(valor) {
    const canales = [0, 2, 4].map(i => parseInt(valor.slice(i, i + 2), 16) / 255);
    const lineales = canales.map(c => c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    return lineales[0] * 0.2126 + lineales[1] * 0.7152 + lineales[2] * 0.0722;
  }
  const fondo = luminancia(color);
  const textoOscuro = luminancia(oscuro.slice(1));
  const blanco = 1.05 / (fondo + 0.05);
  const contrasteOscuro = (Math.max(fondo, textoOscuro) + 0.05) / (Math.min(fondo, textoOscuro) + 0.05);
  return blanco >= contrasteOscuro ? '#ffffff' : oscuro;
}
