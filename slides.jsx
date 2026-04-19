// slides.jsx — 4 variaciones del carrusel "5 conceptos de IA" adaptado a LAiB
// Todas usan DM Sans + Roboto Mono + paleta negro/blanco/rojo LAiB
// Slide: 1080×1080, renderizado a 420×420

const SLIDE_SIZE = 1080;
const DISPLAY_SIZE = 420;
const SCALE = DISPLAY_SIZE / SLIDE_SIZE;

function SlideFrame({ children, bg = '#ffffff' }) {
  return (
    <div style={{
      width: DISPLAY_SIZE, height: DISPLAY_SIZE,
      overflow: 'hidden', position: 'relative', background: bg,
    }}>
      <div className="slide-native" style={{
        width: SLIDE_SIZE, height: SLIDE_SIZE,
        transform: `scale(${SCALE})`, transformOrigin: '0 0',
        position: 'relative', background: bg,
      }}>
        {children}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// CONTENIDO
// ═══════════════════════════════════════════════════════════════════════
const CONTENT = {
  title: '5 conceptos de IA',
  subtitle: 'que todos deberían entender',
  author: 'LAiB',
  concepts: [
    { num: '01', title: 'Modelo', desc: 'Un sistema entrenado con datos para hacer predicciones. No "piensa": reconoce patrones.', tag: 'fundamento' },
    { num: '02', title: 'Prompt', desc: 'La instrucción que le das a una IA. Cuanto más clara, mejor la respuesta.', tag: 'interacción' },
    { num: '03', title: 'Alucinación', desc: 'Cuando la IA inventa información con confianza. Siempre verificá los datos críticos.', tag: 'límites' },
  ],
  cta: {
    title: 'Seguí aprendiendo',
    desc: 'Humanos + AI. Ese es el camino. Seguinos para más contenido sobre inteligencia artificial aplicada.',
    handle: '@laib',
  },
};

// ═══════════════════════════════════════════════════════════════════════
// Helper: patrón de símbolo mariposa repetido (propagación de conocimiento)
// ═══════════════════════════════════════════════════════════════════════
function ButterflyPattern({ color = '#ffffff', opacity = 0.08, size = 120, cols = 6, rows = 6 }) {
  const items = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      items.push(
        <div key={`${r}-${c}`} style={{
          position: 'absolute',
          top: r * size, left: c * size,
          width: size, height: size,
          opacity,
        }}>
          <LaibSymbol size={size * 0.7} color={color} style={{ margin: size * 0.15 }} />
        </div>
      );
    }
  }
  return <>{items}</>;
}

// Footer consistente en todas las variaciones — LAiB branding
function LaibFooter({ page, total = 5, color = LAIB.gray600, accent = LAIB.red, mono = true }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      fontFamily: mono ? LAIB.fontMono : LAIB.fontSans, fontSize: 22,
      color, fontWeight: 500,
    }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
        <LaibSymbol size={28} color={accent} /> LAiB
      </span>
      <span>{String(page).padStart(2, '0')} / {String(total).padStart(2, '0')}</span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// VARIACIÓN 1 — EDITORIAL
// DM Sans con pesos mixtos, números grandes, toque gradiente en portada y CTA
// ═══════════════════════════════════════════════════════════════════════
function EditorialSlide({ index, content }) {
  const bg = LAIB.white;
  const ink = LAIB.black;
  const muted = LAIB.gray600;
  const accent = LAIB.red;

  if (index === 0) {
    return (
      <SlideFrame bg={bg}>
        <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <LaibLockup size={34} color={ink} symbolColor={accent} />
            <div style={{
              fontFamily: LAIB.fontMono, fontSize: 20, color: muted,
              letterSpacing: 2, textTransform: 'uppercase',
            }}>Ed. 01 · Fundamentos</div>
          </div>

          <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
            <div>
              <div style={{
                fontFamily: LAIB.fontSans, fontSize: 280, fontWeight: 800,
                color: ink, lineHeight: 0.88, letterSpacing: -10, display: 'flex', alignItems: 'baseline',
              }}>
                5<span style={{ color: accent, fontSize: 280, lineHeight: 0.88 }}>.</span>
              </div>
              <div style={{
                fontFamily: LAIB.fontSans, fontSize: 92, fontWeight: 700,
                color: ink, lineHeight: 1, marginTop: 16, letterSpacing: -3,
              }}>conceptos de IA</div>
              <div style={{
                fontFamily: LAIB.fontSans, fontSize: 46, fontWeight: 400,
                color: muted, lineHeight: 1.15, marginTop: 20, maxWidth: 800,
              }}>que todos deberían entender</div>
            </div>
          </div>

          <LaibFooter page={1} accent={accent} />
        </div>
      </SlideFrame>
    );
  }

  if (index >= 1 && index <= 3) {
    const c = content.concepts[index - 1];
    return (
      <SlideFrame bg={bg}>
        <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <LaibLockup size={28} color={ink} symbolColor={accent} />
            <div style={{
              fontFamily: LAIB.fontMono, fontSize: 20, color: muted,
              letterSpacing: 2, textTransform: 'uppercase',
            }}>{c.tag}</div>
          </div>

          <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
            <div>
              <div style={{
                fontFamily: LAIB.fontSans, fontSize: 360, fontWeight: 800,
                color: accent, lineHeight: 0.85, letterSpacing: -12,
              }}>{c.num}</div>
              <div style={{
                fontFamily: LAIB.fontSans, fontSize: 130, fontWeight: 700,
                color: ink, lineHeight: 1, letterSpacing: -4, marginTop: 16,
              }}>{c.title}</div>
              <div style={{
                fontFamily: LAIB.fontSans, fontSize: 36, fontWeight: 400,
                color: muted, lineHeight: 1.4, marginTop: 40, maxWidth: 860,
              }}>{c.desc}</div>
            </div>
          </div>

          <div style={{ borderTop: `1px solid ${LAIB.gray200}`, paddingTop: 24 }}>
            <LaibFooter page={index + 1} accent={accent} />
          </div>
        </div>
      </SlideFrame>
    );
  }

  // CTA — con gradiente LAiB
  return (
    <SlideFrame bg={LAIB.black}>
      <div style={{
        position: 'absolute', inset: 0, background: LAIB.gradient, opacity: 0.9,
      }} />
      <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column', color: LAIB.white }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <LaibLockup size={34} color={LAIB.white} symbolColor={LAIB.white} />
          <div style={{
            fontFamily: LAIB.fontMono, fontSize: 20,
            letterSpacing: 2, textTransform: 'uppercase', opacity: 0.8,
          }}>Fin</div>
        </div>

        <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
          <div>
            <div style={{
              fontFamily: LAIB.fontSans, fontSize: 130, fontWeight: 800,
              lineHeight: 0.95, letterSpacing: -4,
            }}>Humanos<br/>+ AI.</div>
            <div style={{
              fontFamily: LAIB.fontSans, fontSize: 40, fontWeight: 500,
              lineHeight: 1.3, marginTop: 40, maxWidth: 800, opacity: 0.95,
            }}>LAiB acelera ese camino. Seguinos para más contenido.</div>
          </div>
        </div>

        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          fontFamily: LAIB.fontMono, fontSize: 24, fontWeight: 500,
        }}>
          <span style={{ fontSize: 32 }}>{content.cta.handle}</span>
          <span style={{ opacity: 0.8 }}>Guardá este post ✓</span>
        </div>
      </div>
    </SlideFrame>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// VARIACIÓN 2 — SWISS GRID
// Retícula estricta, líneas finas, mucho blanco, rojo como único acento
// ═══════════════════════════════════════════════════════════════════════
function SwissSlide({ index, content }) {
  const bg = LAIB.white;
  const ink = LAIB.black;
  const muted = LAIB.gray500;
  const line = LAIB.black;
  const accent = LAIB.red;

  const Header = ({ right }) => (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      borderBottom: `1px solid ${line}`, paddingBottom: 20,
    }}>
      <LaibLockup size={26} color={ink} symbolColor={accent} />
      <span style={{
        fontFamily: LAIB.fontMono, fontSize: 18, fontWeight: 500,
        textTransform: 'uppercase', letterSpacing: 1.5,
      }}>{right}</span>
    </div>
  );

  const Footer = ({ page }) => (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      borderTop: `1px solid ${line}`, paddingTop: 20,
      fontFamily: LAIB.fontMono, fontSize: 18, fontWeight: 500,
    }}>
      <span>{String(page).padStart(2, '0')} / 05</span>
      <span>{page < 5 ? 'Desliza →' : content.cta.handle}</span>
    </div>
  );

  if (index === 0) {
    return (
      <SlideFrame bg={bg}>
        <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column' }}>
          <Header right="№ 01 · Fundamentos" />

          <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 60, alignItems: 'end', paddingTop: 80 }}>
            <div>
              <div style={{
                fontFamily: LAIB.fontMono, fontSize: 18, fontWeight: 500,
                textTransform: 'uppercase', letterSpacing: 3, marginBottom: 40, color: accent,
              }}>Fundamentos</div>
              <div style={{
                fontFamily: LAIB.fontSans, fontSize: 104, fontWeight: 800,
                color: ink, lineHeight: 0.95, letterSpacing: -3.5,
              }}>5 conceptos<br/>de IA<span style={{ color: accent }}>.</span></div>
            </div>
            <div style={{ alignSelf: 'end' }}>
              <div style={{
                fontFamily: LAIB.fontSans, fontSize: 30, fontWeight: 400,
                color: ink, lineHeight: 1.4,
              }}>Una guía corta y clara para entender la inteligencia artificial. Sin tecnicismos.</div>
              <div style={{
                width: 80, height: 2, background: accent, marginTop: 32,
              }} />
            </div>
          </div>

          <Footer page={1} />
        </div>
      </SlideFrame>
    );
  }

  if (index >= 1 && index <= 3) {
    const c = content.concepts[index - 1];
    return (
      <SlideFrame bg={bg}>
        <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column' }}>
          <Header right={c.tag} />

          <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '160px 1fr', gap: 40, paddingTop: 80 }}>
            <div style={{
              fontFamily: LAIB.fontMono, fontSize: 20, fontWeight: 500,
              color: accent, borderTop: `2px solid ${accent}`, paddingTop: 12,
            }}>{c.num}</div>
            <div>
              <div style={{
                fontFamily: LAIB.fontSans, fontSize: 168, fontWeight: 800,
                color: ink, lineHeight: 0.9, letterSpacing: -6, marginBottom: 56,
              }}>{c.title}<span style={{ color: accent }}>.</span></div>
              <div style={{
                fontFamily: LAIB.fontSans, fontSize: 38, fontWeight: 400,
                color: ink, lineHeight: 1.4, maxWidth: 760,
              }}>{c.desc}</div>
            </div>
          </div>

          <Footer page={index + 1} />
        </div>
      </SlideFrame>
    );
  }

  return (
    <SlideFrame bg={bg}>
      <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column' }}>
        <Header right="Final" />

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{
            fontFamily: LAIB.fontMono, fontSize: 18, fontWeight: 500,
            textTransform: 'uppercase', letterSpacing: 3, marginBottom: 32, color: accent,
          }}>Seguí con nosotros</div>
          <div style={{
            fontFamily: LAIB.fontSans, fontSize: 128, fontWeight: 800,
            color: ink, lineHeight: 0.95, letterSpacing: -4, marginBottom: 40,
          }}>Humanos<br/>+ AI<span style={{ color: accent }}>.</span></div>
          <div style={{
            fontFamily: LAIB.fontSans, fontSize: 32, fontWeight: 400,
            color: ink, lineHeight: 1.4, maxWidth: 780,
          }}>{content.cta.desc}</div>
        </div>

        <Footer page={5} />
      </div>
    </SlideFrame>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// VARIACIÓN 3 — BOLD / TIPOGRÁFICO
// Fondos intensos (negro, rojo, gradiente), texto gigante DM Sans ExtraBold
// ═══════════════════════════════════════════════════════════════════════
function BoldSlide({ index, content }) {
  // Esquema por slide
  const schemes = [
    { type: 'black', bg: LAIB.black, ink: LAIB.white, accent: LAIB.red },
    { type: 'white', bg: LAIB.white, ink: LAIB.black, accent: LAIB.red },
    { type: 'red', bg: LAIB.red, ink: LAIB.white, accent: LAIB.black },
    { type: 'black', bg: LAIB.black, ink: LAIB.white, accent: LAIB.red },
    { type: 'gradient', bg: LAIB.black, ink: LAIB.white, accent: LAIB.white },
  ];
  const s = schemes[index];

  if (index === 0) {
    return (
      <SlideFrame bg={s.bg}>
        <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', opacity: 0.06 }}>
          <ButterflyPattern color={s.ink} size={180} cols={7} rows={7} opacity={1} />
        </div>
        <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column', color: s.ink }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <LaibLockup size={36} color={s.ink} symbolColor={s.accent} />
            <span style={{
              fontFamily: LAIB.fontMono, fontSize: 22, fontWeight: 500,
              letterSpacing: 2, textTransform: 'uppercase', opacity: 0.7,
            }}>→ Aprendé IA</span>
          </div>

          <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
            <div style={{
              fontFamily: LAIB.fontSans, fontSize: 270, fontWeight: 800,
              lineHeight: 0.82, letterSpacing: -12,
            }}>
              IA<br/>
              <span style={{ color: s.accent }}>para</span><br/>
              todos.
            </div>
          </div>

          <div style={{
            fontFamily: LAIB.fontSans, fontSize: 30, fontWeight: 500, lineHeight: 1.3,
            opacity: 0.85,
          }}>5 conceptos clave. Sin tecnicismos. En 5 slides.</div>
        </div>
      </SlideFrame>
    );
  }

  if (index >= 1 && index <= 3) {
    const c = content.concepts[index - 1];
    return (
      <SlideFrame bg={s.bg}>
        <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column', color: s.ink }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <LaibLockup size={28} color={s.ink} symbolColor={s.accent} />
            <span style={{
              fontFamily: LAIB.fontMono, fontSize: 22, fontWeight: 500,
              letterSpacing: 1.5, textTransform: 'uppercase',
            }}>#{c.num} · {c.tag}</span>
          </div>

          <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
            <div style={{
              fontFamily: LAIB.fontSans, fontSize: 280, fontWeight: 800,
              lineHeight: 0.82, letterSpacing: -12,
            }}>
              {c.title}
              <span style={{ color: s.accent }}>.</span>
            </div>
          </div>

          <div style={{
            fontFamily: LAIB.fontSans, fontSize: 38, fontWeight: 500, lineHeight: 1.3,
            maxWidth: 880,
          }}>{c.desc}</div>
        </div>
      </SlideFrame>
    );
  }

  // CTA con gradiente LAiB
  return (
    <SlideFrame bg={LAIB.black}>
      <div style={{ position: 'absolute', inset: 0, background: LAIB.gradient }} />
      <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column', color: LAIB.white }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <LaibLockup size={36} color={LAIB.white} symbolColor={LAIB.white} />
          <span style={{
            fontFamily: LAIB.fontMono, fontSize: 22, fontWeight: 500,
            letterSpacing: 2, textTransform: 'uppercase', opacity: 0.9,
          }}>↓ Tu turno</span>
        </div>

        <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
          <div style={{
            fontFamily: LAIB.fontSans, fontSize: 200, fontWeight: 800,
            lineHeight: 0.85, letterSpacing: -8,
          }}>
            Humanos<br/>
            + AI<span>.</span>
          </div>
        </div>

        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end',
        }}>
          <div style={{
            fontFamily: LAIB.fontSans, fontSize: 40, fontWeight: 700,
          }}>{content.cta.handle}</div>
          <div style={{
            fontFamily: LAIB.fontMono, fontSize: 22, fontWeight: 500,
            opacity: 0.85,
          }}>Guardá · Compartí</div>
        </div>
      </div>
    </SlideFrame>
  );
}

// ═══════════════════════════════════════════════════════════════════════
// VARIACIÓN 4 — MONO / TÉCNICO
// Roboto Mono (tipografía del logotipo LAiB), estética de código, sobria
// ═══════════════════════════════════════════════════════════════════════
function MonoSlide({ index, content }) {
  const bg = LAIB.white;
  const ink = LAIB.black;
  const muted = LAIB.gray500;
  const accent = LAIB.red;
  const line = LAIB.gray200;
  const mono = LAIB.fontMono;

  const Header = ({ right }) => (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      borderBottom: `1px dashed ${line}`, paddingBottom: 24,
      fontFamily: mono, fontSize: 20, color: muted, fontWeight: 500,
    }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 12 }}>
        <LaibSymbol size={28} color={accent} /> laib.md
      </span>
      <span>{right}</span>
    </div>
  );

  const Footer = ({ page }) => (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      borderTop: `1px dashed ${line}`, paddingTop: 24,
      fontFamily: mono, fontSize: 20, color: muted, fontWeight: 500,
    }}>
      <span>{content.cta.handle}</span>
      <span>[{String(page).padStart(2, '0')}/05] {page < 5 ? '→' : '★'}</span>
    </div>
  );

  if (index === 0) {
    return (
      <SlideFrame bg={bg}>
        <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column' }}>
          <Header right="[ intro ]" />

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <div style={{ fontFamily: mono, fontSize: 24, color: accent, marginBottom: 32, fontWeight: 500 }}>
              # capítulo_01
            </div>
            <div style={{
              fontFamily: mono, fontSize: 96, color: ink, lineHeight: 1.05,
              letterSpacing: -2, fontWeight: 700, marginBottom: 40,
            }}>
              5 conceptos<br/>
              <span style={{ color: muted }}>{'>'}</span> de IA
            </div>
            <div style={{
              fontFamily: mono, fontSize: 26, color: muted, lineHeight: 1.5, maxWidth: 820, fontWeight: 400,
            }}>
              {'// el futuro no es AI vs humanos.'}<br/>
              {'// es humanos + AI.'}
            </div>
          </div>

          <Footer page={1} />
        </div>
      </SlideFrame>
    );
  }

  if (index >= 1 && index <= 3) {
    const c = content.concepts[index - 1];
    return (
      <SlideFrame bg={bg}>
        <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column' }}>
          <Header right={`[ ${c.tag} ]`} />

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <div style={{ fontFamily: mono, fontSize: 26, color: accent, marginBottom: 20, fontWeight: 500 }}>
              ## {c.num}
            </div>
            <div style={{
              fontFamily: mono, fontSize: 140, color: ink, lineHeight: 1,
              letterSpacing: -4, fontWeight: 700, marginBottom: 56,
            }}>
              {c.title}<span style={{ color: accent }}>()</span>
            </div>

            <div style={{
              background: LAIB.gray100, padding: 40, border: `1px solid ${line}`,
              fontFamily: mono, fontSize: 30, color: ink, lineHeight: 1.5,
              position: 'relative', fontWeight: 400,
            }}>
              <div style={{
                position: 'absolute', top: -14, left: 32, background: bg,
                padding: '0 16px', fontSize: 18, color: muted, fontWeight: 500,
              }}>docs.txt</div>
              <span style={{ color: accent, fontWeight: 500 }}>{'>'}</span> {c.desc}
            </div>
          </div>

          <Footer page={index + 1} />
        </div>
      </SlideFrame>
    );
  }

  return (
    <SlideFrame bg={bg}>
      <div style={{ position: 'absolute', inset: 0, padding: 70, display: 'flex', flexDirection: 'column' }}>
        <Header right="[ outro ]" />

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontFamily: mono, fontSize: 24, color: accent, marginBottom: 32, fontWeight: 500 }}>
            # end_of_file
          </div>
          <div style={{
            fontFamily: mono, fontSize: 92, color: ink, lineHeight: 1.1,
            letterSpacing: -2, fontWeight: 700, marginBottom: 48,
          }}>
            return<span style={{ color: accent }}>(</span><br/>
            <span style={{ paddingLeft: 60 }}>"humanos + AI"</span><br/>
            <span style={{ color: accent }}>)</span>
          </div>
          <div style={{
            fontFamily: mono, fontSize: 26, color: muted, lineHeight: 1.5, fontWeight: 400,
          }}>
            {'// ¿útil? guardá el post.'}<br/>
            {'// ¿muy útil? compartilo.'}
          </div>
        </div>

        <Footer page={5} />
      </div>
    </SlideFrame>
  );
}

// Export
Object.assign(window, {
  SlideFrame, CONTENT, ButterflyPattern, LaibFooter,
  EditorialSlide, SwissSlide, BoldSlide, MonoSlide,
});
