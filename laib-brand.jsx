// laib-brand.jsx — tokens de marca LAiB + símbolo mariposa SVG

const LAIB = {
  // Paleta principal
  black: '#000000',
  white: '#ffffff',
  red: '#f52525',

  // Gradiente (naranja → rojo → púrpura → violeta)
  gradient: 'linear-gradient(135deg, #fda80d 0%, #f52525 33%, #87006e 66%, #42008e 100%)',
  gradientStops: ['#fda80d', '#f52525', '#87006e', '#42008e'],

  // Grises
  gray900: '#191919',
  gray800: '#333333',
  gray700: '#4D4D4D',
  gray600: '#666666',
  gray500: '#7F7F7F',
  gray400: '#999999',
  gray300: '#B3B3B3',
  gray200: '#CCCCCC',
  gray100: '#E6E6E6',

  // Tipografía
  fontSans: '"DM Sans", sans-serif',
  fontMono: '"Roboto Mono", ui-monospace, monospace',
};

// Símbolo LAiB — mariposa formada por 4 círculos convergentes.
// Composición simétrica: dos círculos superiores (alas superiores) + dos inferiores (alas inferiores)
// tocándose en el centro. Recreación fiel de la descripción del manual.
function LaibSymbol({ size = 120, color = LAIB.red, style = {} }) {
  // 4 círculos tangentes en el centro, formando una mariposa abstracta
  // Canvas 100x100, centro en (50,50)
  const r = 25; // radio de cada círculo
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={style} aria-label="LAiB">
      {/* Alas superiores — ligeramente más pequeñas/inclinadas */}
      <circle cx="30" cy="35" r={r} fill={color} />
      <circle cx="70" cy="35" r={r} fill={color} />
      {/* Alas inferiores */}
      <circle cx="30" cy="65" r={r} fill={color} />
      <circle cx="70" cy="65" r={r} fill={color} />
      {/* Centro (intersección) queda definida por el overlap */}
    </svg>
  );
}

// Wordmark LAiB en Roboto Mono — "L", "A", "i" minúscula, "B"
function LaibWordmark({ size = 48, color = LAIB.black, style = {} }) {
  return (
    <span style={{
      fontFamily: LAIB.fontMono,
      fontWeight: 500,
      fontSize: size,
      color,
      letterSpacing: -size * 0.02,
      lineHeight: 1,
      ...style,
    }}>LAiB</span>
  );
}

// Lockup: símbolo + wordmark
function LaibLockup({ size = 48, color = LAIB.black, symbolColor, style = {} }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: size * 0.35,
      ...style,
    }}>
      <LaibSymbol size={size * 1.1} color={symbolColor ?? color} />
      <LaibWordmark size={size} color={color} />
    </span>
  );
}

Object.assign(window, { LAIB, LaibSymbol, LaibWordmark, LaibLockup });
