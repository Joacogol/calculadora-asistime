-- Publicación en Instagram: la cola y la cuenta conectada.
--
-- Se corre UNA VEZ en el Supabase de cada cliente que vaya a publicar, desde
-- el SQL Editor. Es aditivo: no toca `disenos` ni nada de lo que ya anda.
--
-- Los clientes nuevos ya lo traen incorporado en `base-de-un-cliente.sql`.


-- ── Funciones auxiliares ──────────────────────────────────────────────────
-- Las bases viejas —las que se armaron cuando el sistema servía a un solo
-- cliente— tienen estos disparadores con otro nombre: `tocar_actualizado_en` y
-- `forzar_marca`. Se crean acá con los nombres del esquema nuevo en vez de
-- renombrar los viejos: los disparadores de `disenos` siguen colgando de los
-- suyos y no se toca nada de lo que ya anda. En una base nueva ya existen y
-- esto las reemplaza por lo mismo.
create or replace function public.tocar_actualizado()
returns trigger language plpgsql
set search_path = public, pg_temp
as $$ begin new.actualizado_en := now(); return new; end $$;

-- El user_id sale de la sesión, no del cliente: si lo mandara el frontend,
-- cualquiera podría programar un posteo a nombre de otro.
create or replace function public.forzar_user_id()
returns trigger language plpgsql security definer set search_path = public, pg_temp
as $$ begin new.user_id := auth.uid(); return new; end $$;

revoke execute on function public.tocar_actualizado() from anon, authenticated;
revoke execute on function public.forzar_user_id()   from anon, authenticated;


-- ── La cuenta de Instagram ────────────────────────────────────────────────
-- El token vive en la base del cliente y no en Secret Manager, a diferencia de
-- las otras claves del sistema. Tres razones:
--
--   1. Es del cliente. Su cuenta, su base. Si mañana se lleva el proyecto, se
--      lleva su conexión: no hay nada suyo en un Secret Manager mío.
--   2. Se vence a los 60 días y hay que renovarlo. Renovar significa ESCRIBIR,
--      y el worker ya escribe en esta base todo el tiempo. Escribir en Secret
--      Manager pedía darle al worker permiso de crear versiones de secretos,
--      que es un permiso mucho más grande que el que necesita para nada más.
--   3. Un cliente puede conectar más de una cuenta. Una fila por cuenta.
--
-- RLS prendido y NINGUNA política: es la forma de decir «acá no entra nadie».
-- La service_role del worker no pasa por RLS y es la única que lee el token.
create table if not exists public.cuentas_ig (
  id          uuid primary key default gen_random_uuid(),
  creado_en   timestamptz not null default now(),
  usuario     text,                    -- @boss.padel, para mostrarlo en la app
  ig_user_id  text,                    -- lo completa el worker en la 1ª corrida
  token       text not null,
  renovado_en timestamptz not null default now(),
  expira_en   timestamptz,             -- 60 días desde que se generó
  activa      boolean not null default true,
  mensaje     text                     -- por qué se desactivó, si se desactivó
);

alter table public.cuentas_ig enable row level security;
revoke all on public.cuentas_ig from anon, authenticated;

-- La app SÍ necesita saber si hay cuenta y cuándo se vence, para mostrar el
-- botón o pedir reconectar. Esta vista expone eso y NADA del token.
-- Es `security_invoker = off` a propósito —corre con los permisos del dueño y
-- por eso puede leer una tabla que tiene RLS sin políticas—. Es exactamente el
-- caso de uso legítimo del patrón: una ventana angosta a una tabla cerrada.
create or replace view public.instagram_estado
with (security_invoker = off) as
select
  usuario,
  activa,
  expira_en,
  (expira_en is not null and expira_en < now() + interval '7 days') as por_vencer,
  mensaje
from public.cuentas_ig;

grant select on public.instagram_estado to authenticated;


-- ── La cola de publicación ────────────────────────────────────────────────
-- Una fila por posteo, no por diseño. Un mismo diseño puede dar un carrusel de
-- feed y tres stories: son tres publicaciones distintas, con su propio horario
-- y su propio resultado.
--
-- `urls` va ORDENADO: es el orden en que se ven las diapositivas del carrusel,
-- que es media pieza. Por eso es un array y no una relación.
create table if not exists public.publicaciones (
  id             uuid primary key default gen_random_uuid(),
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  user_id        uuid references auth.users(id) on delete set null,
  diseno_id      uuid references public.disenos(id) on delete cascade,
  tipo           text not null default 'post',
  urls           text[] not null default '{}',
  caption        text,
  publicar_en    timestamptz not null default now(),
  estado         text not null default 'programado',
  contenedor     text,          -- id del contenedor de Instagram, mientras procesa
  ig_id          text,          -- id del posteo ya publicado
  permalink      text,          -- el link para abrirlo
  mensaje        text,          -- el error, en castellano, si falló
  intentos       int  not null default 0,   -- reintentos por error
  esperas        int  not null default 0,   -- vueltas esperando un video
  constraint tipo_pub_valido check (tipo in ('post','carrusel','story','reel')),
  constraint estado_pub_valido check (
    estado in ('programado','subiendo','publicado','error','cancelado'))
);

-- El índice que usa el worker en cada corrida: «qué toca publicar ahora».
create index if not exists publicaciones_cola_idx
  on public.publicaciones (estado, publicar_en);
create index if not exists publicaciones_diseno_idx
  on public.publicaciones (diseno_id);
create index if not exists publicaciones_user_idx
  on public.publicaciones (user_id, creado_en desc);

drop trigger if exists publicaciones_tocar on public.publicaciones;
create trigger publicaciones_tocar before update on public.publicaciones
  for each row execute function public.tocar_actualizado();

drop trigger if exists publicaciones_forzar_user on public.publicaciones;
create trigger publicaciones_forzar_user before insert on public.publicaciones
  for each row execute function public.forzar_user_id();

alter table public.publicaciones enable row level security;

drop policy if exists "programar lo propio" on public.publicaciones;
-- El `with check` compara contra user_id y no sólo contra «hay sesión»: el
-- disparador ya lo puso, así que si algún día alguien borra el disparador esto
-- falla cerrado en vez de dejar pasar filas sin dueño.
create policy "programar lo propio" on public.publicaciones
  for insert to authenticated with check (auth.uid() = user_id);

drop policy if exists "ver lo propio pub" on public.publicaciones;
create policy "ver lo propio pub" on public.publicaciones
  for select to authenticated using (auth.uid() = user_id);

-- La persona puede cancelar o correr la fecha de algo que TODAVÍA no salió.
-- Una vez publicado, la fila es historia y no se toca: el posteo ya está en
-- Instagram y editar la fila sólo serviría para que la app mienta.
drop policy if exists "cambiar lo no publicado" on public.publicaciones;
create policy "cambiar lo no publicado" on public.publicaciones
  for update to authenticated
  using (auth.uid() = user_id and estado in ('programado','error'))
  with check (auth.uid() = user_id and estado in ('programado','cancelado'));


-- ── Tiempo real ───────────────────────────────────────────────────────────
-- Mismo motivo que en `disenos`: sin esto la tarjeta se queda en «Programado»
-- aunque el posteo ya esté publicado, y sólo se entera recargando.
-- El `do` es para poder correr este archivo dos veces sin que explote: agregar
-- una tabla que ya está en la publicación es un error, no un no-op.
do $$
begin
  alter publication supabase_realtime add table public.publicaciones;
exception when duplicate_object then null;
end $$;

alter table public.publicaciones replica identity full;
