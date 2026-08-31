-- ═══════════════════════════════════════════════════════════════════════════
--  Alta del MONTAJE DE REELS para un cliente
-- ═══════════════════════════════════════════════════════════════════════════
--
--  Deja la base lista para que el cliente pueda mandar sus propios videos y
--  recibir un reel editado: cortado, encuadrado en 9:16, con los tiempos
--  muertos afuera y con subtítulos sacados de lo que se dice.
--
--  **No habilita el motor de video por IA.** Son dos cosas distintas y con
--  precios que no se parecen: generar un video con IA sale miles de créditos y
--  se configura en el `marca.json`; montar material propio no cuesta nada y
--  sólo necesita esta tabla. Un cliente puede tener esto y no aquello.
--
--  Es IDEMPOTENTE: correrlo dos veces no hace nada la segunda. Sirve tanto
--  para una base que ya tiene la tabla `reels` (le agrega las columnas) como
--  para una que no la tiene (la crea entera).

create table if not exists reels (
  id                  uuid primary key default gen_random_uuid(),
  creado_en           timestamptz not null default now(),
  actualizado_en      timestamptz not null default now(),
  user_id             uuid,
  mensaje             text not null,
  -- Opcional: un reel montado con material propio no parte de ninguna foto.
  foto                text,
  titulo              text,
  kicker              text,
  bajada              text,
  musica              text,
  estado              text not null default 'pendiente',
  modelo              text,
  resolucion          text,
  duracion            integer,
  tarea               text,
  clip_url            text,
  url                 text,
  quien               text,
  mensaje_agente      text,
  notas               text,
  creditos_estimados  integer,
  creditos_gastados   integer,
  metricas            jsonb
);

-- Para una base que ya tenía la tabla del camino de IA.
alter table reels add column if not exists clips jsonb;
alter table reels add column if not exists guion jsonb;
alter table reels alter column foto drop not null;

comment on column reels.clips is
  'Material propio: lista de URLs de video que manda el agente. Si esta columna '
  'tiene algo, el reel se MONTA con ese material y no interviene ningún modelo: '
  'no gasta créditos.';
comment on column reels.guion is
  'El guion de edición: tramos (qué pedazo de cada clip), subtitulos (en la '
  'escala del reel montado, o "auto" para sacarlos del audio), cortar_silencios '
  'y musica. El contrato completo está en motor/guion.py.';

create index if not exists reels_estado_creado on reels (estado, creado_en);

-- El worker entra con la service_role, así que no necesita políticas. Se deja
-- RLS prendida igual: sin políticas, la clave anónima no ve nada, que es lo
-- que corresponde para una tabla que sólo tocan el worker y las funciones.
alter table reels enable row level security;
