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
--
--  ── Por qué todo está calificado con `public.` ──────────────────────
--
--  Esto empezó siendo una migración para los clientes que tenían proyecto
--  propio, donde todo vive en `public` y escribir `reels` a secas alcanzaba.
--  Desde que hay clientes de ESQUEMA COMPARTIDO, este archivo también lo
--  compone `herramientas/esquema-de-cliente.py`, y esa herramienta traduce un
--  alta a otro esquema reemplazando el texto `public.`. Sin la calificación,
--  `create table reels` caía donde apuntara el `search_path` — en la práctica,
--  en `public`, o sea en la base de otro cliente.
--
--  Se descubrió el 8/9/2026 y de la peor manera posible: no falló nada. Life
--  Montevideo y Larrique se dieron de alta sin tabla `reels` y nadie se
--  enteró hasta que alguien pidió el primer video, semanas después, y la API
--  contestó «Could not find the table 'larrique.reels'».

create table if not exists public.reels (
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
alter table public.reels add column if not exists clips jsonb;
alter table public.reels add column if not exists guion jsonb;
alter table public.reels alter column foto drop not null;

comment on column public.reels.clips is
  'Material propio: lista de URLs de video que manda el agente. Si esta columna '
  'tiene algo, el reel se MONTA con ese material y no interviene ningún modelo: '
  'no gasta créditos.';
comment on column public.reels.guion is
  'El guion de edición: tramos (qué pedazo de cada clip), subtitulos (en la '
  'escala del reel montado, o "auto" para sacarlos del audio), cortar_silencios '
  'y musica. El contrato completo está en motor/guion.py.';

create index if not exists reels_estado_creado on public.reels (estado, creado_en);

-- El worker entra con la service_role, así que no necesita políticas. Se deja
-- RLS prendida igual: sin políticas, la clave anónima no ve nada, que es lo
-- que corresponde para una tabla que sólo tocan el worker y las funciones.
alter table public.reels enable row level security;


-- ── Que `actualizado_en` se actualice de verdad ────────────────────────────
--
-- La columna estaba desde el principio; el trigger que la escribe, no. Una
-- columna llamada `actualizado_en` que nunca cambia no se lee como rota: se
-- lee como que la fila no se tocó, que es peor, porque nadie va a mirarla.
--
-- De ahí cuelga la detección de pedidos colgados: `_colgada()` mide contra
-- `actualizado_en` a propósito, y NO contra `creado_en`, porque un reel que
-- estuvo dos horas esperando la clave de Magnific nacería vencido y se daría
-- por perdido en la primera corrida después de pagarse el video. Sin trigger,
-- `actualizado_en` ES `creado_en` y vuelve exactamente ese error.
--
-- El 2/9/2026 Asistime y Clínica tenían la tabla sin ninguno de los dos
-- triggers, y Boss y Stadium con los dos: los suyos se habían hecho a mano
-- antes de que existiera esta migración, así que el agujero sólo lo veía un
-- cliente nuevo. Se arreglaron a mano y se agregan acá para que no vuelva.
create or replace function public.tocar_actualizado() returns trigger
  language plpgsql set search_path to 'public', 'pg_temp'
  as $$ begin new.actualizado_en := now(); return new; end $$;

create or replace function public.forzar_user_id() returns trigger
  language plpgsql security definer set search_path to 'public', 'pg_temp'
  as $$ begin new.user_id := auth.uid(); return new; end $$;

-- `drop` + `create` porque Postgres no tiene `create trigger if not exists`, y
-- correr esto dos veces tiene que ser inofensivo.
drop trigger if exists reels_tocar on public.reels;
create trigger reels_tocar before update on public.reels
  for each row execute function public.tocar_actualizado();

drop trigger if exists reels_forzar_user on public.reels;
create trigger reels_forzar_user before insert on public.reels
  for each row execute function public.forzar_user_id();
