-- La base de un cliente nuevo: las cuatro tablas que tienen que existir ANTES
-- de `plantillas.sql`, `plantilla-pedidos.sql` y `motor-pedidos.sql`.
--
-- Se corre una vez, en el Supabase de ese cliente. Es re-corrible: si algo ya
-- está, no falla ni pisa datos.
--
-- De dónde salió este archivo: se reconstruyó leyendo la base viva de Clínica
-- Preventiva —que es el cliente de referencia— y se aplicó a Stadium. Después
-- se compararon las dos bases columna por columna, política por política y
-- trigger por trigger. Los nombres de los `check` pueden no coincidir con los
-- de Clínica: eso no lo ve nadie más que Postgres.
--
-- Los `on delete` de las claves foráneas NO son decoración. Si una persona se
-- borra de `auth.users` y sus filas la apuntan sin regla, el borrado FALLA:
-- Postgres no deja quedar una referencia colgada. Con `set null` la fila queda
-- sin dueño y la historia se conserva. `publicaciones` va con `cascade` porque
-- una publicación de un diseño que ya no existe no significa nada.
--
-- No hay columna de marca en ninguna tabla, a propósito: cada cliente tiene su
-- propio proyecto de Supabase, así que de qué marca es una fila está
-- determinado por dónde vive. Una columna `marca` sería una invitación a
-- juntar dos clientes en una base, que es exactamente lo que no queremos.


-- ═══ Los dos ayudantes de los triggers ═══════════════════════════════════
--
-- `forzar_user_id` es la razón por la que las políticas de abajo pueden
-- confiar en `user_id`: el cliente no lo manda, lo pone la base. Si lo mandara
-- él, podría mandar el de otro.

create or replace function public.tocar_actualizado() returns trigger
language plpgsql set search_path = public, pg_temp as $$
begin new.actualizado_en := now(); return new; end $$;

create or replace function public.forzar_user_id() returns trigger
language plpgsql security definer set search_path = public, pg_temp as $$
begin new.user_id := auth.uid(); return new; end $$;

-- Los dos de abajo hacen lo mismo que los dos de arriba y existen sólo porque
-- `disenos` es la tabla más vieja del sistema y se armó antes de que los
-- ayudantes fueran compartidos. Se dejan para que la base de un cliente nuevo
-- sea idéntica a la del cliente de referencia y las dos se puedan comparar.

create or replace function public.disenos_tocar_actualizado() returns trigger
language plpgsql set search_path = public, pg_temp as $$
begin new.actualizado_en := now(); return new; end $$;

create or replace function public.disenos_forzar_user_id() returns trigger
language plpgsql security definer set search_path = public as $$
begin new.user_id := auth.uid(); return new; end $$;


-- ═══ disenos — los pedidos de pieza ══════════════════════════════════════

create table if not exists public.disenos (
  id             uuid primary key default gen_random_uuid(),
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  user_id        uuid references auth.users(id) on delete set null,
  mensaje        text not null,          -- lo que pidió el cliente, tal cual
  formatos       text[] not null default '{post}',
  sede           text,
  quien          text,
  estado         text not null default 'pendiente',
  titulo         text,
  urls           text[] default '{}',    -- las piezas terminadas
  "copy"         text,
  -- El spec.json exacto con el que se dibujó la pieza. Sin esto, corregir un
  -- diseño es imposible: cada pedido de cambio lo rehace desde cero y sale
  -- otra pieza. Ver DESPLEGAR.md, 5/9/2026.
  spec           jsonb,
  -- El diseño que este pedido viene a corregir. Con esto puesto, el worker
  -- parte de SU spec y cambia sólo lo que se pide.
  corrige        uuid references public.disenos(id) on delete set null,
  mensaje_agente text,
  documentos     jsonb default '[]'::jsonb,
  videos         jsonb default '[]'::jsonb,
  adjuntos       jsonb default '[]'::jsonb,
  metricas       jsonb default '{}'::jsonb,
  fotos_elegidas text[] not null default '{}',
  logo_socio     text,
  notas          text,
  constraint disenos_estado_valido
    check (estado in ('pendiente','generando','listo','error'))
);

-- Columnas que se sumaron después del primer cliente. Van sueltas para que
-- este archivo sirva igual en una base recién creada que en una que ya venía.
alter table public.disenos add column if not exists documentos     jsonb default '[]'::jsonb;
alter table public.disenos add column if not exists videos         jsonb default '[]'::jsonb;
alter table public.disenos add column if not exists adjuntos       jsonb default '[]'::jsonb;
alter table public.disenos add column if not exists metricas       jsonb default '{}'::jsonb;
alter table public.disenos add column if not exists fotos_elegidas text[] not null default '{}';
alter table public.disenos add column if not exists logo_socio     text;
alter table public.disenos add column if not exists notas          text;

comment on table  public.disenos is
  'Pedidos de diseño de la app del cliente. El worker (Cloud Run) los lee con la service_role key y sube las piezas al bucket `disenos`.';
comment on column public.disenos."copy" is
  'Texto del posteo, listo para publicar. No lleva notas ni encabezados.';
comment on column public.disenos.notas is
  'Decisiones y supuestos del diseñador. Es para quien pidió la pieza: nunca se publica.';

create index if not exists disenos_estado_idx
  on public.disenos (estado, creado_en);
create index if not exists disenos_user_creado_idx
  on public.disenos (user_id, creado_en desc);

drop trigger if exists disenos_forzar_user on public.disenos;
create trigger disenos_forzar_user before insert on public.disenos
  for each row execute function public.disenos_forzar_user_id();

drop trigger if exists disenos_tocar on public.disenos;
create trigger disenos_tocar before update on public.disenos
  for each row execute function public.disenos_tocar_actualizado();

alter table public.disenos enable row level security;

-- Cada uno ve lo suyo y nada más. El worker no pasa por acá: entra con la
-- service_role key, que se saltea RLS.
drop policy if exists "ver lo propio" on public.disenos;
create policy "ver lo propio" on public.disenos
  for select to authenticated using (auth.uid() = user_id);

drop policy if exists "crear lo propio" on public.disenos;
create policy "crear lo propio" on public.disenos
  for insert to authenticated with check (auth.uid() is not null);

-- No hay política de update ni de delete, y es a propósito: un pedido ya hecho
-- no se edita. Si hay que cambiarlo, se pide otro.


-- ═══ fotos — el banco de imágenes del cliente ════════════════════════════

create table if not exists public.fotos (
  id          uuid primary key default gen_random_uuid(),
  creado_en   timestamptz not null default now(),
  user_id     uuid references auth.users(id) on delete set null,
  clave       text not null,          -- la ruta dentro del bucket
  url         text not null,
  descripcion text,                   -- qué se ve; es lo que lee el diseñador
  etiquetas   text[] not null default '{}',
  quien       jsonb  not null default '{}'::jsonb,
  foco        jsonb  not null default '{}'::jsonb,
  ancho       int,
  alto        int,
  activa      boolean not null default true
);

create unique index if not exists fotos_clave_idx on public.fotos (clave);
create index if not exists fotos_activa_idx on public.fotos (activa, creado_en desc);

drop trigger if exists fotos_forzar_user on public.fotos;
create trigger fotos_forzar_user before insert on public.fotos
  for each row execute function public.forzar_user_id();

alter table public.fotos enable row level security;

-- El banco es de la marca, no de quien subió cada foto: lo ve y lo edita
-- cualquiera del equipo. Sumar sí queda a nombre de uno.
drop policy if exists "ver el banco" on public.fotos;
create policy "ver el banco" on public.fotos
  for select to authenticated using (true);

drop policy if exists "sumar al banco" on public.fotos;
create policy "sumar al banco" on public.fotos
  for insert to authenticated with check (auth.uid() = user_id);

drop policy if exists "editar el banco" on public.fotos;
create policy "editar el banco" on public.fotos
  for update to authenticated using (true) with check (true);


-- ═══ cuentas_ig — el token de Instagram ══════════════════════════════════

create table if not exists public.cuentas_ig (
  id          uuid primary key default gen_random_uuid(),
  creado_en   timestamptz not null default now(),
  usuario     text,
  ig_user_id  text,
  token       text not null,
  renovado_en timestamptz not null default now(),
  expira_en   timestamptz,
  activa      boolean not null default true,
  mensaje     text
);

alter table public.cuentas_ig enable row level security;

-- RLS prendido y NINGUNA política, a propósito. Acá vive un token que publica
-- en el Instagram del cliente: sin política, `authenticated` no lee ni una
-- fila. Sólo llega el worker, con la service_role key. Si alguna vez hay que
-- mostrar la cuenta conectada en la app, se agrega una política que devuelva
-- `usuario` y `activa` — nunca `token`.


-- La cara pública de `cuentas_ig`: todo menos el token. La consulta
-- `api-publicar` antes de encolar nada —sin cuenta conectada, la fila
-- quedaría esperando para siempre y el chat diría «ya sale»— y sirve para
-- mostrar en la app qué cuenta está conectada.
--
-- **Faltaba acá.** Existía a mano en Boss y en Clínica, así que Asistime la
-- descubrió el 3/9/2026 cuando publicar ya estaba armado: la función contesta
-- «esta marca no tiene Instagram conectado» y el motivo real es que la vista
-- no existe. Ahora el cliente que viene la recibe con la base.
--
-- `security_invoker` no es un detalle: sin él la vista corre con los permisos
-- de su dueño y se saltea el RLS de `cuentas_ig` —que no tiene políticas
-- justamente para que nadie la lea—, así que cualquiera con la clave `anon`
-- vería el usuario de Instagram del cliente y el vencimiento de su token.
create or replace view public.instagram_estado
with (security_invoker = on) as
  select usuario,
         activa,
         expira_en,
         (expira_en is not null and expira_en < now() + interval '7 days') as por_vencer,
         mensaje
    from public.cuentas_ig;

revoke all on public.instagram_estado from anon;
grant select on public.instagram_estado to authenticated, service_role;


-- ═══ publicaciones — la cola de posteo ═══════════════════════════════════

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
  contenedor     text,                -- el id del contenedor de Meta
  ig_id          text,
  permalink      text,
  mensaje        text,
  intentos       int not null default 0,
  esperas        int not null default 0,
  constraint publicaciones_tipo_valido
    check (tipo in ('post','carrusel','story','reel')),
  constraint publicaciones_estado_valido
    check (estado in ('programado','subiendo','publicado','error','cancelado'))
);

create index if not exists publicaciones_cola_idx
  on public.publicaciones (estado, publicar_en);
create index if not exists publicaciones_user_idx
  on public.publicaciones (user_id, creado_en desc);
create index if not exists publicaciones_diseno_idx
  on public.publicaciones (diseno_id);

drop trigger if exists publicaciones_forzar_user on public.publicaciones;
create trigger publicaciones_forzar_user before insert on public.publicaciones
  for each row execute function public.forzar_user_id();

drop trigger if exists publicaciones_tocar on public.publicaciones;
create trigger publicaciones_tocar before update on public.publicaciones
  for each row execute function public.tocar_actualizado();

alter table public.publicaciones enable row level security;

drop policy if exists "ver lo propio pub" on public.publicaciones;
create policy "ver lo propio pub" on public.publicaciones
  for select to authenticated using (auth.uid() = user_id);

drop policy if exists "programar lo propio" on public.publicaciones;
create policy "programar lo propio" on public.publicaciones
  for insert to authenticated with check (auth.uid() = user_id);

-- Se puede cambiar o cancelar mientras NO haya salido. `subiendo` queda afuera
-- de las dos listas: si el worker ya lo está mandando a Meta, editarlo desde
-- la app dejaría la fila diciendo una cosa y el posteo siendo otra.
drop policy if exists "cambiar lo no publicado" on public.publicaciones;
create policy "cambiar lo no publicado" on public.publicaciones
  for update to authenticated
  using       (auth.uid() = user_id and estado in ('programado','error'))
  with check  (auth.uid() = user_id and estado in ('programado','cancelado'));


-- ═══ El bucket `disenos` ═════════════════════════════════════════════════
--
-- Público de lectura porque Instagram tiene que poder bajarse la imagen por
-- URL para publicarla. Escribir es otra cosa: va por las políticas de abajo.

insert into storage.buckets (id, name, public)
values ('disenos', 'disenos', true)
on conflict (id) do update set public = true;

-- Tres carpetas y tres permisos distintos, en vez de "subir a donde sea":
--   fotos/    el banco de la marca — cualquiera del equipo
--   socios/   logos de terceros — cualquiera del equipo
--   adjuntos/<user_id>/  lo que manda una persona con su pedido — sólo suyo
-- El worker sube las piezas terminadas con la service_role key, que no pasa
-- por acá.
drop policy if exists "subir al banco" on storage.objects;
create policy "subir al banco" on storage.objects
  for insert to authenticated with check (
    bucket_id = 'disenos' and (storage.foldername(name))[1] = 'fotos');

drop policy if exists "subir logos de socios" on storage.objects;
create policy "subir logos de socios" on storage.objects
  for insert to authenticated with check (
    bucket_id = 'disenos' and (storage.foldername(name))[1] = 'socios');

drop policy if exists "subir mis adjuntos" on storage.objects;
create policy "subir mis adjuntos" on storage.objects
  for insert to authenticated with check (
    bucket_id = 'disenos'
    and (storage.foldername(name))[1] = 'adjuntos'
    and (storage.foldername(name))[2] = auth.uid()::text);
